module GitHubGateway

using Test
using HTTP
using JSON
using Sockets

include("gateway.jl")

@testset "Gateway Tests" begin
    @testset "Service Registration" begin
        config = GatewayConfig(port=8081)
        gw = Gateway(config)
        
        register_service(gw, "test_service", "http://localhost:8000")
        
        @test gw.services["test_service"].name == "test_service"
        @test gw.services["test_service"].url == "http://localhost:8000"
    end
    
    @testset "Health Check" begin
        config = GatewayConfig(port=8082)
        gw = Gateway(config)
        
        register_service(gw, "test", "http://localhost:9999")
        healthy = check_health(gw, "test")
        
        @test healthy == false
    end
    
    @testset "API Response Format" begin
        response = APIResponse(success=true, data=Dict("test"=>"value"))
        json_str = JSON.json(response)
        parsed = JSON.parse(json_str)
        
        @test parsed["success"] == true
        @test parsed["data"]["test"] == "value"
    end
end

end
