package main

import (
	"context"
	"encoding/json"
	"log"
	"net/http"
	"sync"
	"time"

	"github.com/gin-gonic/gin"
	"github.com/gorilla/websocket"
	"github.com/prometheus/client_golang/prometheus/promhttp"
)

type GatewayConfig struct {
	Port         string
	ReadTimeout  time.Duration
	WriteTimeout time.Duration
}

type ServiceEndpoint struct {
	Name    string
	URL     string
	Healthy bool
	Latency time.Duration
}

type Gateway struct {
	config     GatewayConfig
	services   map[string]*ServiceEndpoint
	mu         sync.RWMutex
	upgrader   websocket.Upgrader
	httpClient *http.Client
}

type HealthStatus struct {
	Status    string                     `json:"status"`
	Timestamp time.Time                  `json:"timestamp"`
	Services  map[string]ServiceEndpoint `json:"services"`
}

type APIResponse struct {
	Success bool                   `json:"success"`
	Data    interface{}            `json:"data,omitempty"`
	Error   string                 `json:"error,omitempty"`
	Meta    map[string]interface{} `json:"meta,omitempty"`
}

func NewGateway(cfg GatewayConfig) *Gateway {
	return &Gateway{
		config:   cfg,
		services: make(map[string]*ServiceEndpoint),
		upgrader: websocket.Upgrader{
			ReadBufferSize:  1024,
			WriteBufferSize: 1024,
			CheckOrigin: func(r *http.Request) bool {
				return true
			},
		},
		httpClient: &http.Client{
			Timeout: 10 * time.Second,
		},
	}
}

func (g *Gateway) RegisterService(name, url string) {
	g.mu.Lock()
	defer g.mu.Unlock()
	g.services[name] = &ServiceEndpoint{
		Name:    name,
		URL:     url,
		Healthy: false,
	}
}

func (g *Gateway) CheckServiceHealth(name string) bool {
	g.mu.RLock()
	svc, exists := g.services[name]
	g.mu.RUnlock()

	if !exists {
		return false
	}

	start := time.Now()
	resp, err := g.httpClient.Get(svc.URL + "/health")
	latency := time.Since(start)

	g.mu.Lock()
	defer g.mu.Unlock()
	svc.Healthy = err == nil && resp.StatusCode == http.StatusOK
	svc.Latency = latency

	if resp != nil {
		resp.Body.Close()
	}

	return svc.Healthy
}

func (g *Gateway) ProxyRequest(c *gin.Context, serviceName string) {
	g.mu.RLock()
	svc, exists := g.services[serviceName]
	g.mu.RUnlock()

	if !exists {
		c.JSON(http.StatusNotFound, APIResponse{
			Success: false,
			Error:   "Service not found",
		})
		return
	}

	targetURL := svc.URL + c.Request.URL.Path
	req, err := http.NewRequestWithContext(c.Request.Context(), c.Request.Method, targetURL, c.Request.Body)
	if err != nil {
		c.JSON(http.StatusInternalServerError, APIResponse{
			Success: false,
			Error:   err.Error(),
		})
		return
	}

	req.Header = c.Request.Header.Clone()
	resp, err := g.httpClient.Do(req)
	if err != nil {
		c.JSON(http.StatusBadGateway, APIResponse{
			Success: false,
			Error:   "Service unavailable: " + err.Error(),
		})
		return
	}
	defer resp.Body.Close()

	for k, v := range resp.Header {
		c.Header(k, v[0])
	}

	c.DataFromReader(resp.StatusCode, resp.ContentLength, resp.Header.Get("Content-Type"), resp.Body, nil)
}

func (g *Gateway) HandleWebSocket(c *gin.Context) {
	serviceName := c.Query("service")
	if serviceName == "" {
		c.JSON(http.StatusBadRequest, gin.H{"error": "service parameter required"})
		return
	}

	conn, err := g.upgrader.Upgrade(c.Writer, c.Request, nil)
	if err != nil {
		log.Printf("WebSocket upgrade error: %v", err)
		return
	}
	defer conn.Close()

	g.mu.RLock()
	svc, exists := g.services[serviceName]
	g.mu.RUnlock()

	if !exists {
		conn.WriteMessage(websocket.TextMessage, []byte(`{"error":"service not found"}`))
		return
	}

	for {
		_, msg, err := conn.ReadMessage()
		if err != nil {
			log.Printf("WebSocket read error: %v", err)
			break
		}

		req, err := http.NewRequestWithContext(context.Background(), "POST", svc.URL+"/ws", nil)
		if err != nil {
			continue
		}

		resp, err := g.httpClient.Do(req)
		if err != nil {
			conn.WriteMessage(websocket.TextMessage, []byte(`{"error":"service unavailable"}`))
			continue
		}
		defer resp.Body.Close()

		conn.WriteMessage(websocket.TextMessage, []byte(`{"status":"ok"}`))
	}
}

func (g *Gateway) HealthHandler(c *gin.Context) {
	g.mu.RLock()
	servicesCopy := make(map[string]ServiceEndpoint)
	for k, v := range g.services {
		servicesCopy[k] = *v
	}
	g.mu.RUnlock()

	healthy := true
	for _, svc := range servicesCopy {
		if !svc.Healthy {
			healthy = false
			break
		}
	}

	c.JSON(http.StatusOK, HealthStatus{
		Status:    map[bool]string{true: "healthy", false: "degraded"}[healthy],
		Timestamp: time.Now(),
		Services:  servicesCopy,
	})
}

func (g *Gateway) MetricsHandler() gin.HandlerFunc {
	h := promhttp.Handler()
	return func(c *gin.Context) {
		h.ServeHTTP(c.Writer, c.Request)
	}
}

func (g *Gateway) LoggingMiddleware() gin.HandlerFunc {
	return func(c *gin.Context) {
		start := time.Now()
		path := c.Request.URL.Path

		c.Next()

		latency := time.Since(start)
		status := c.Writer.Status()

		log.Printf("[%s] %s %s %d %v",
			time.Now().Format("2006-01-02 15:04:05"),
			c.Request.Method,
			path,
			status,
			latency,
		)
	}
}

func (g *Gateway) CORSMiddleware() gin.HandlerFunc {
	return func(c *gin.Context) {
		c.Header("Access-Control-Allow-Origin", "*")
		c.Header("Access-Control-Allow-Methods", "GET, POST, PUT, DELETE, OPTIONS")
		c.Header("Access-Control-Allow-Headers", "Content-Type, Authorization, X-Requested-With")

		if c.Request.Method == "OPTIONS" {
			c.AbortWithStatus(http.StatusNoContent)
			return
		}

		c.Next()
	}
}

func (g *Gateway) Start() {
	router := gin.Default()

	router.Use(g.LoggingMiddleware())
	router.Use(g.CORSMiddleware())

	router.GET("/health", g.HealthHandler)
	router.GET("/metrics", g.MetricsHandler())

	api := router.Group("/api/v1")
	{
		api.GET("/services", func(c *gin.Context) {
			g.mu.RLock()
			defer g.mu.RUnlock()
			c.JSON(http.StatusOK, APIResponse{
				Success: true,
				Data:    g.services,
			})
		})

		api.POST("/services/:name/check", func(c *gin.Context) {
			name := c.Param("name")
			healthy := g.CheckServiceHealth(name)
			c.JSON(http.StatusOK, APIResponse{
				Success: true,
				Data: map[string]interface{}{
					"service": name,
					"healthy": healthy,
				},
			})
		})

		api.Any("/proxy/:service/*path", func(c *gin.Context) {
			service := c.Param("service")
			g.ProxyRequest(c, service)
		})
	}

	router.GET("/ws", g.HandleWebSocket)

	srv := &http.Server{
		Addr:         g.config.Port,
		Handler:      router,
		ReadTimeout:  g.config.ReadTimeout,
		WriteTimeout: g.config.WriteTimeout,
	}

	log.Printf("🚀 Gateway starting on %s", g.config.Port)
	if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
		log.Fatalf("Gateway failed: %v", err)
	}
}

func main() {
	cfg := GatewayConfig{
		Port:         ":8080",
		ReadTimeout:  30 * time.Second,
		WriteTimeout: 30 * time.Second,
	}

	gateway := NewGateway(cfg)

	gateway.RegisterService("bot", "http://localhost:5000")
	gateway.RegisterService("dashboard", "http://localhost:3000")
	gateway.RegisterService("mobile", "http://localhost:4000")

	go func() {
		ticker := time.NewTicker(10 * time.Second)
		for range ticker.C {
			for name := range gateway.services {
				gateway.CheckServiceHealth(name)
			}
		}
	}()

	gateway.Start()
}
