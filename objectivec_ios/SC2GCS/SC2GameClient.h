#import <Foundation/Foundation.h>

NS_ASSUME_NONNULL_BEGIN

@interface SC2GameClient : NSObject

@property (nonatomic, copy) NSString *host;
@property (nonatomic, assign) NSInteger port;
@property (nonatomic, strong, nullable) NSURLSessionWebSocketTask *webSocketTask;

- (void)connectWithHost:(NSString *)host port:(NSInteger)port;
- (void)disconnect;
- (void)sendCommand:(NSDictionary *)command;
- (void)onMessage:(void (^)(NSDictionary *message))handler;

@end

NS_ASSUME_NONNULL_END
