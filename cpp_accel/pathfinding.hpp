#pragma once

#include <vector>
#include <cmath>
#include <queue>
#include <limits>
#include <functional>
#include <algorithm>

namespace swarm {

struct Point2D {
    double x, y;
    Point2D() : x(0), y(0) {}
    Point2D(double x_, double y_) : x(x_), y(y_) {}
    
    double distance_to(const Point2D& other) const {
        double dx = x - other.x;
        double dy = y - other.y;
        return std::sqrt(dx * dx + dy * dy);
    }
    
    bool operator==(const Point2D& other) const {
        return std::abs(x - other.x) < 1e-9 && std::abs(y - other.y) < 1e-9;
    }
};

struct Node {
    Point2D pos;
    double g_cost;
    double h_cost;
    double f_cost() const { return g_cost + h_cost; }
    Point2D parent;
    bool has_parent;
    
    Node(const Point2D& p, double g, double h, const Point2D& par = Point2D(), bool has_par = false)
        : pos(p), g_cost(g), h_cost(h), parent(par), has_parent(has_par) {}
};

struct CompareNode {
    bool operator()(const Node& a, const Node& b) const {
        return a.f_cost() > b.f_cost();
    }
};

class AStarPathfinder {
public:
    AStarPathfinder(int grid_width, int grid_height, double resolution)
        : grid_width_(grid_width), grid_height_(grid_height), resolution_(resolution) {}
    
    std::vector<Point2D> find_path(const Point2D& start, const Point2D& goal) {
        std::vector<Point2D> path;
        
        int start_gx = world_to_grid(start.x);
        int start_gy = world_to_grid(start.y);
        int goal_gx = world_to_grid(goal.x);
        int goal_gy = world_to_grid(goal.y);
        
        if (!is_valid(start_gx, start_gy) || !is_valid(goal_gx, goal_gy)) {
            return path;
        }
        
        std::priority_queue<Node, std::vector<Node>, CompareNode> open_set;
        bool closed[100][100] = {{false}};
        
        open_set.emplace(Point2D(start_gx, start_gy), 0.0, heuristic(start_gx, start_gy, goal_gx, goal_gy));
        
        while (!open_set.empty()) {
            Node current = open_set.top();
            open_set.pop();
            
            int cx = static_cast<int>(current.pos.x);
            int cy = static_cast<int>(current.pos.y);
            
            if (cx == goal_gx && cy == goal_gy) {
                return reconstruct_path(current, goal);
            }
            
            if (closed[cx][cy]) continue;
            closed[cx][cy] = true;
            
            const int dx[] = {-1, 1, 0, 0, -1, -1, 1, 1};
            const int dy[] = {0, 0, -1, 1, -1, 1, -1, 1};
            
            for (int i = 0; i < 8; ++i) {
                int nx = cx + dx[i];
                int ny = cy + dy[i];
                
                if (!is_valid(nx, ny) || closed[nx][ny]) continue;
                
                double move_cost = (i < 4) ? 1.0 : 1.414;
                double new_g = current.g_cost + move_cost;
                double h = heuristic(nx, ny, goal_gx, goal_gy);
                
                open_set.emplace(Point2D(nx, ny), new_g, h, current.pos, true);
            }
        }
        
        return path;
    }
    
    void add_obstacle(int grid_x, int grid_y) {
        if (is_valid(grid_x, grid_y)) {
            obstacles_.insert({grid_x, grid_y});
        }
    }
    
    void clear_obstacles() {
        obstacles_.clear();
    }
    
private:
    int grid_width_;
    int grid_height_;
    double resolution_;
    std::set<std::pair<int, int>> obstacles_;
    
    int world_to_grid(double world_coord) const {
        return static_cast<int>(world_coord / resolution_);
    }
    
    double grid_to_world(int grid_coord) const {
        return grid_coord * resolution_;
    }
    
    bool is_valid(int x, int y) const {
        return x >= 0 && x < grid_width_ && y >= 0 && y < grid_height_ &&
               obstacles_.find({x, y}) == obstacles_.end();
    }
    
    double heuristic(int x1, int y1, int x2, int y2) const {
        double dx = std::abs(x1 - x2);
        double dy = std::abs(y1 - y2);
        return dx + dy + (1.414 - 2) * std::min(dx, dy);
    }
    
    std::vector<Point2D> reconstruct_path(const Node& end_node, const Point2D& goal) {
        std::vector<Point2D> path;
        path.push_back(goal);
        
        Point2D current = end_node.pos;
        while (end_node.has_parent) {
            path.push_back(Point2D(grid_to_world(current.x), grid_to_world(current.y)));
            current = end_node.parent;
        }
        
        std::reverse(path.begin(), path.end());
        return path;
    }
};

struct PotentialField {
    struct Point {
        double x, y;
    };
    
    static double attractive_force(const Point& pos, const Point& goal, double k_att = 1.0) {
        double dx = goal.x - pos.x;
        double dy = goal.y - pos.y;
        return k_att * std::sqrt(dx * dx + dy * dy);
    }
    
    static Point attractive_gradient(const Point& pos, const Point& goal, double k_att = 1.0) {
        return {k_att * (goal.x - pos.x), k_att * (goal.y - pos.y)};
    }
    
    static double repulsive_force(const Point& pos, const Point& obstacle, double influence_radius, double k_rep = 100.0) {
        double dist = std::sqrt(std::pow(pos.x - obstacle.x, 2) + std::pow(pos.y - obstacle.y, 2));
        if (dist > influence_radius) return 0.0;
        if (dist < 1e-6) dist = 1e-6;
        return k_rep * std::pow(1.0 / dist - 1.0 / influence_radius, 2);
    }
    
    static Point repulsive_gradient(const Point& pos, const Point& obstacle, double influence_radius, double k_rep = 100.0) {
        double dist = std::sqrt(std::pow(pos.x - obstacle.x, 2) + std::pow(pos.y - obstacle.y, 2));
        if (dist > influence_radius || dist < 1e-6) return {0.0, 0.0};
        
        double factor = k_rep * (1.0 / dist - 1.0 / influence_radius) / (dist * dist);
        return {factor * (pos.x - obstacle.x), factor * (pos.y - obstacle.y)};
    }
};

extern "C" {
    
    void* create_pathfinder(int grid_width, int grid_height, double resolution) {
        return new swarm::AStarPathfinder(grid_width, grid_height, resolution);
    }
    
    void delete_pathfinder(void* pathfinder) {
        delete static_cast<swarm::AStarPathfinder*>(pathfinder);
    }
    
    void add_obstacle(void* pathfinder, int x, int y) {
        static_cast<swarm::AStarPathfinder*>(pathfinder)->add_obstacle(x, y);
    }
    
    void clear_obstacles(void* pathfinder) {
        static_cast<swarm::AStarPathfinder*>(pathfinder)->clear_obstacles();
    }
    
    int find_path(
        void* pathfinder,
        double start_x, double start_y,
        double goal_x, double goal_y,
        double* out_x, double* out_y,
        int max_points
    ) {
        auto pf = static_cast<swarm::AStarPathfinder*>(pathfinder);
        auto path = pf->find_path(
            swarm::Point2D(start_x, start_y),
            swarm::Point2D(goal_x, goal_y)
        );
        
        int count = std::min(static_cast<int>(path.size()), max_points);
        for (int i = 0; i < count; ++i) {
            out_x[i] = path[i].x;
            out_y[i] = path[i].y;
        }
        return count;
    }
    
    double path_distance(double* x, double* y, int count) {
        if (count < 2) return 0.0;
        double total = 0.0;
        for (int i = 1; i < count; ++i) {
            double dx = x[i] - x[i-1];
            double dy = y[i] - y[i-1];
            total += std::sqrt(dx * dx + dy * dy);
        }
        return total;
    }
    
    double smooth_path_quality(double* x, double* y, int count) {
        if (count < 3) return 1.0;
        
        double total_curvature = 0.0;
        for (int i = 1; i < count - 1; ++i) {
            double v1x = x[i] - x[i-1];
            double v1y = y[i] - y[i-1];
            double v2x = x[i+1] - x[i];
            double v2y = y[i+1] - y[i];
            
            double dot = v1x * v2x + v1y * v2y;
            double mag1 = std::sqrt(v1x * v1x + v1y * v1y);
            double mag2 = std::sqrt(v2x * v2x + v2y * v2y);
            
            if (mag1 > 1e-9 && mag2 > 1e-9) {
                double cos_angle = dot / (mag1 * mag2);
                total_curvature += 1.0 - cos_angle;
            }
        }
        
        return 1.0 / (1.0 + total_curvature / count);
    }
}

}
