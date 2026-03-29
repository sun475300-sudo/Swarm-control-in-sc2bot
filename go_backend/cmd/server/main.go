package main

import (
	"context"
	"log"
	"net"
	"sync"
	"time"

	"github.com/sun475300/go_backend/internal/service"
	pb "github.com/sun475300/go_backend/proto"
	"google.golang.org/grpc"
)

type GCSServer struct {
	pb.UnimplementedGCSServer
	mu        sync.RWMutex
	botStatus *pb.StatusResponse
	gameState *pb.GameStateResponse
	replays   []*pb.ReplayInfo
}

func NewGCSServer() *GCSServer {
	return &GCSServer{
		botStatus: &pb.StatusResponse{
			BotName:       "Wicked Zerg",
			Phase:         "Phase 61",
			WinRate:       "14%",
			GamesPlayed:   100,
			GamesWon:      14,
			IsRunning:     true,
			UptimeSeconds: 86400,
			CpuUsage:      45.5,
			MemoryUsage:   512.0,
		},
		gameState: &pb.GameStateResponse{
			MapName:          "AbyssalReefLE",
			GameTimeSeconds:  300,
			EnemyRace:        "Protoss",
			MySupply:         120,
			EnemySupply:      100,
			CurrentPhase:     "Mid-Game",
			EstimatedWinProb: 0.35,
		},
		replays: generateSampleReplays(),
	}
}

func generateSampleReplays() []*pb.ReplayInfo {
	replays := make([]*pb.ReplayInfo, 20)
	results := []string{"Victory", "Defeat", "Victory", "Defeat", "Victory"}
	races := []string{"Terran", "Zerg", "Protoss", "Terran", "Protoss"}
	maps := []string{"AbyssalReefLE", "WorldOfSleepersLE", "NeonVioletPremakeLE", "GresvanLE", "AcropolisLE"}

	for i := 0; i < 20; i++ {
		replays[i] = &pb.ReplayInfo{
			ReplayId:        "replay_" + string(rune('0'+i)),
			MapName:         maps[i%len(maps)],
			EnemyRace:       races[i%len(races)],
			Result:          results[i%len(results)],
			DurationSeconds: int32(300 + i*30),
			Timestamp:       time.Now().Add(-time.Duration(i) * time.Hour).Format(time.RFC3339),
			PriorityScore:   float32(0.5 + float64(i%10)*0.05),
		}
	}
	return replays
}

func (s *GCSServer) GetBotStatus(ctx context.Context, req *pb.StatusRequest) (*pb.StatusResponse, error) {
	s.mu.RLock()
	defer s.mu.RUnlock()
	return s.botStatus, nil
}

func (s *GCSServer) GetGameState(ctx context.Context, req *pb.GameStateRequest) (*pb.GameStateResponse, error) {
	s.mu.RLock()
	defer s.mu.RUnlock()
	return s.gameState, nil
}

func (s *GCSServer) SendCommand(ctx context.Context, req *pb.CommandRequest) (*pb.CommandResponse, error) {
	start := time.Now()
	log.Printf("Received command: %s with params: %v", req.Command, req.Parameters)

	return &pb.CommandResponse{
		Success:         true,
		Message:         "Command executed successfully",
		ExecutionTimeMs: time.Since(start).Milliseconds(),
	}, nil
}

func (s *GCSServer) StreamTelemetry(req *pb.StreamRequest, stream pb.GCSServer_StreamTelemetryServer) error {
	log.Printf("Starting telemetry stream for bot: %s", req.BotId)

	ticker := time.NewTicker(2 * time.Second)
	defer ticker.Stop()

	for {
		select {
		case <-stream.Context().Done():
			return nil
		case <-ticker.C:
			event := &pb.TelemetryEvent{
				Timestamp: time.Now().Unix(),
				EventType: "heartbeat",
				GameTime:  int32(time.Now().Unix() % 1000),
				Data: map[string]string{
					"cpu_usage":    "45.5",
					"memory_usage": "512MB",
					"games_played": "100",
				},
			}
			if err := stream.Send(event); err != nil {
				return err
			}
		}
	}
}

func (s *GCSServer) GetReplayList(ctx context.Context, req *pb.ReplayListRequest) (*pb.ReplayListResponse, error) {
	s.mu.RLock()
	defer s.mu.RUnlock()

	start := int(req.Offset)
	end := start + int(req.Limit)
	if end > len(s.replays) {
		end = len(s.replays)
	}
	if start > len(s.replays) {
		start = len(s.replays)
	}

	return &pb.ReplayListResponse{
		Replays:    s.replays[start:end],
		TotalCount: int32(len(s.replays)),
	}, nil
}

func main() {
	lis, err := net.Listen("tcp", ":50051")
	if err != nil {
		log.Fatalf("Failed to listen: %v", err)
	}

	s := grpc.NewServer()
	pb.RegisterGCSServer(s, NewGCSServer())

	log.Println("GCS Server listening on :50051")
	if err := s.Serve(lis); err != nil {
		log.Fatalf("Failed to serve: %v", err)
	}
}
