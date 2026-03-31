// Phase 495: Apache Camel Integration Routes for SC2 Data Pipeline
// Routes: SC2 game events -> Kafka -> processing -> database
// Components: timer, kafka, jdbc, rest, file
// Error handling: onException, deadLetterChannel

package io.sc2bot.camel;

import org.apache.camel.builder.RouteBuilder;
import org.apache.camel.model.rest.RestBindingMode;
import org.springframework.stereotype.Component;

@Component
public class SC2Routes extends RouteBuilder {

    @Override
    public void configure() throws Exception {

        // Global error handler with dead letter channel
        errorHandler(deadLetterChannel("kafka:sc2-dead-letter-queue")
            .maximumRedeliveries(3)
            .redeliveryDelay(1000)
            .backOffMultiplier(2)
            .useExponentialBackOff()
            .logExhausted(true));

        // Handle specific exceptions
        onException(Exception.class)
            .handled(true)
            .log("SC2 route error: ${exception.message}")
            .to("kafka:sc2-error-events");

        // REST API configuration
        restConfiguration()
            .component("netty-http")
            .host("0.0.0.0")
            .port(8080)
            .bindingMode(RestBindingMode.json)
            .dataFormatProperty("prettyPrint", "true");

        // REST endpoint: receive SC2 game events
        rest("/sc2/events")
            .post("/game")
                .type(GameEvent.class)
                .to("direct:process-game-event")
            .get("/stats")
                .to("direct:get-stats");

        // Route 1: Process incoming game events -> Kafka
        from("direct:process-game-event")
            .routeId("game-event-ingestion")
            .log("Received SC2 game event: ${body}")
            .marshal().json()
            .to("kafka:sc2-game-events?brokers=kafka:9092"
                + "&groupId=sc2-camel-producer"
                + "&valueSerializer=org.apache.kafka.common.serialization.StringSerializer")
            .log("Published to Kafka: ${body}");

        // Route 2: Consume Kafka -> process -> store in DB
        from("kafka:sc2-game-events?brokers=kafka:9092"
                + "&groupId=sc2-camel-consumers"
                + "&autoOffsetReset=earliest")
            .routeId("game-event-processor")
            .unmarshal().json(GameEvent.class)
            .process(exchange -> {
                GameEvent event = exchange.getIn().getBody(GameEvent.class);
                // Enrich event with computed statistics
                event.setWinRate(computeWinRate(event));
                exchange.getIn().setBody(event);
            })
            .choice()
                .when(simple("${body.eventType} == 'GAME_ENDED'"))
                    .to("direct:save-game-result")
                .when(simple("${body.eventType} == 'UNIT_KILLED'"))
                    .to("direct:update-unit-stats")
                .otherwise()
                    .log("Unknown event type: ${body.eventType}")
            .end();

        // Route 3: Save game result to database
        from("direct:save-game-result")
            .routeId("save-game-result")
            .marshal().json()
            .to("jdbc:sc2DataSource?useHeadersAsParameters=false")
            .log("Saved game result to DB");

        // Route 4: Update unit statistics
        from("direct:update-unit-stats")
            .routeId("update-unit-stats")
            .to("jdbc:sc2DataSource");

        // Route 5: Timer-based stats aggregation -> file export
        from("timer:stats-export?period=3600000")
            .routeId("stats-exporter")
            .to("sql:SELECT * FROM sc2_game_stats WHERE created_at > :?since"
                + "?dataSource=sc2DataSource")
            .marshal().csv()
            .to("file:/exports/sc2-stats?fileName=stats-${date:now:yyyyMMdd-HHmm}.csv")
            .log("Stats exported to file");

        // Route 6: Get stats REST handler
        from("direct:get-stats")
            .routeId("get-stats")
            .to("sql:SELECT COUNT(*) as total_games, AVG(win_rate) as avg_win_rate FROM sc2_game_stats?dataSource=sc2DataSource")
            .marshal().json();
    }

    private double computeWinRate(GameEvent event) {
        return event.getWins() > 0
            ? (double) event.getWins() / (event.getWins() + event.getLosses())
            : 0.0;
    }
}
