// P86: Scala - Analytics Pipeline
// StarCraft II AI Bot - Data Analysis Pipeline

package sc2.analytics

import org.apache.spark.sql.{SparkSession, DataFrame, Dataset, Row, functions => f}
import org.apache.spark.sql.types._
import org.apache.spark.sql.expressions.Window
import java.time.LocalDateTime
import scala.concurrent.Future
import scala.concurrent.ExecutionContext.Implicits.global

object GameAnalyticsPipeline {

  def main(args: Array[String]): Unit = {
    val spark = SparkSession.builder()
      .appName("SC2 AI Analytics")
      .master("local[*]")
      .getOrCreate()

    import spark.implicits._

    println("🚀 Starting SC2 Analytics Pipeline...")

    // Load game data
    val gamesDF = loadGameData(spark)
    val unitsDF = loadUnitData(spark)
    val eventsDF = loadEventData(spark)

    // Run analyses
    val matchupAnalysis = analyzeMatchups(gamesDF)
    val timingAnalysis = analyzeGameTiming(gamesDF)
    val combatAnalysis = analyzeCombat(unitsDF, eventsDF)
    val economyAnalysis = analyzeEconomy(gamesDF)

    // Generate reports
    generateReports(matchupAnalysis, timingAnalysis, combatAnalysis, economyAnalysis)

    spark.stop()
    println("✅ Pipeline Complete!")
  }

  def loadGameData(spark: SparkSession): DataFrame = {
    val schema = StructType(Seq(
      StructField("game_id", StringType, nullable = false),
      StructField("timestamp", TimestampType, nullable = false),
      StructField("map_name", StringType, nullable = true),
      StructField("player_race", StringType, nullable = false),
      StructField("opponent_race", StringType, nullable = false),
      StructField("result", StringType, nullable = false),
      StructField("duration_frames", LongType, nullable = false),
      StructField("apm", IntegerType, nullable = true),
      StructField("mmr_before", IntegerType, nullable = true),
      StructField("mmr_after", IntegerType, nullable = true)
    ))

    spark.read
      .option("header", "true")
      .schema(schema)
      .csv("data/games/*.csv")
  }

  def loadUnitData(spark: SparkSession): DataFrame = {
    spark.read
      .option("header", "true")
      .json("data/units/*.json")
  }

  def loadEventData(spark: SparkSession): DataFrame = {
    spark.read
      .option("header", "true")
      .parquet("data/events/*.parquet")
  }

  def analyzeMatchups(games: DataFrame): DataFrame = {
    import games.sparkSession.implicits._

    games
      .groupBy("opponent_race", "result")
      .agg(f.count("*").as("count"))
      .withColumn("win_rate", 
        f.when(f.col("result") === "WIN", 1.0).otherwise(0.0))
      .groupBy("opponent_race")
      .agg(
        f.sum("count").as("total_games"),
        f.avg("win_rate").as("win_rate")
      )
      .orderBy(f.desc("win_rate"))
  }

  def analyzeGameTiming(games: DataFrame): DataFrame = {
    val minutesCol = f.col("duration_frames") / 22.4 / 60

    games
      .withColumn("game_minutes", f.floor(minutesCol))
      .groupBy("game_minutes", "result")
      .agg(f.count("*").as("games"))
      .orderBy("game_minutes")
  }

  def analyzeCombat(units: DataFrame, events: DataFrame): DataFrame = {
    units
      .filter(f.col("is_combat") === true)
      .groupBy("unit_type", "result")
      .agg(
        f.avg("damage_dealt").as("avg_damage"),
        f.count("*").as("engagements"),
        f.sum(f.when(f.col("result") === "KILL", 1).otherwise(0)).as("kills")
      )
  }

  def analyzeEconomy(games: DataFrame): DataFrame = {
    games
      .groupBy("opponent_race", "result")
      .agg(
        f.avg("apm").as("avg_apm"),
        f.avg(f.col("duration_frames") / 22.4 / 60).as("avg_duration_min")
      )
  }

  def generateReports(
    matchups: DataFrame,
    timing: DataFrame,
    combat: DataFrame,
    economy: DataFrame
  ): Unit = {
    println("\n📊 Matchup Analysis:")
    matchups.show()

    println("\n⏱️ Timing Analysis:")
    timing.show()

    println("\n⚔️ Combat Analysis:")
    combat.show()

    println("\n💰 Economy Analysis:")
    economy.show()

    // Save to output
    matchups.write.mode("overwrite").parquet("output/matchups.parquet")
    timing.write.mode("overwrite").parquet("output/timing.parquet")
    combat.write.mode("overwrite").parquet("output/combat.parquet")
    economy.write.mode("overwrite").parquet("output/economy.parquet")
  }
}

// Real-time streaming analytics
class StreamingAnalytics(spark: SparkSession) {

  import spark.implicits._

  def processGameStream(): Unit = {
    val events = spark.readStream
      .format("socket")
      .option("host", "localhost")
      .option("port", 9999)
      .load()

    val parsed = events
      .select(f.from_json(f.col("value"), Schema.eventSchema).as("data"))
      .select("data.*")

    val query = parsed
      .writeStream
      .format("console")
      .start()

    query.awaitTermination()
  }
}

object Schema {
  val eventSchema = StructType(Seq(
    StructField("event_type", StringType, nullable = false),
    StructField("timestamp", LongType, nullable = false),
    StructField("unit_id", IntegerType, nullable = true),
    StructField("unit_type", StringType, nullable = true),
    StructField("position_x", DoubleType, nullable = true),
    StructField("position_y", DoubleType, nullable = true),
    StructField("target_id", IntegerType, nullable = true),
    StructField("damage", DoubleType, nullable = true)
  ))
}
