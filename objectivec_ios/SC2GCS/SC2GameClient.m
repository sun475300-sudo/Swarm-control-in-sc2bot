#import "SC2GameClient.h"

@implementation SC2GameClient {
    void (^_messageHandler)(NSDictionary *);
}

- (void)connectWithHost:(NSString *)host port:(NSInteger)port {
    self.host = host;
    self.port = port;
    
    NSURL *url = [NSURL URLWithString:[NSString stringWithFormat:@"ws://%@:%ld/game", host, (long)port]];
    NSURLSessionConfiguration *config = [NSURLSessionConfiguration defaultSessionConfiguration];
    NSURLSession *session = [NSURLSession sessionWithConfiguration:config];
    
    self.webSocketTask = [session webSocketTaskWithURL:url];
    [self.webSocketTask resume];
    [self receiveMessage];
}

- (void)receiveMessage {
    __weak typeof(self) weakSelf = self;
    [self.webSocketTask receiveMessageWithCompletionHandler:^(NSURLSessionWebSocketMessage * _Nullable message, NSError * _Nullable error) {
        if (error) return;
        if (message.type == NSURLSessionWebSocketMessageTypeString && weakSelf->_messageHandler) {
            NSData *data = [message.string dataUsingEncoding:NSUTF8StringEncoding];
            NSDictionary *json = [NSJSONSerialization JSONObjectWithData:data options:0 error:nil];
            weakSelf->_messageHandler(json);
        }
        [weakSelf receiveMessage];
    }];
}

- (void)sendCommand:(NSDictionary *)command {
    NSData *data = [NSJSONSerialization dataWithJSONObject:command options:0 error:nil];
    NSString *jsonString = [[NSString alloc] initWithData:data encoding:NSUTF8StringEncoding];
    NSURLSessionWebSocketMessage *message = [[NSURLSessionWebSocketMessage alloc] initWithString:jsonString];
    [self.webSocketTask sendMessage:message completionHandler:^(NSError * _Nullable error) {}];
}

- (void)onMessage:(void (^)(NSDictionary *))handler {
    _messageHandler = handler;
}

- (void)disconnect {
    [self.webSocketTask cancel];
    self.webSocketTask = nil;
}

@end
