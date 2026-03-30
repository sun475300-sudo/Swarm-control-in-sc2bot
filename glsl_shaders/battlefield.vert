#version 300 es
// SC2 Zerg AI Bot — Battlefield Vertex Shader
// Transforms unit world positions to clip space and forwards
// per-unit color and health data to the fragment shader.

// -----------------------------------------------------------------------
// Per-vertex attributes
// -----------------------------------------------------------------------
layout(location = 0) in vec3  a_position;    // unit world-space position
layout(location = 1) in vec3  a_color;       // base faction colour
layout(location = 2) in float a_health;      // normalised [0,1]
layout(location = 3) in float a_selected;    // 1.0 if selected, 0.0 otherwise
layout(location = 4) in vec2  a_texCoord;    // sprite UV

// -----------------------------------------------------------------------
// Uniforms
// -----------------------------------------------------------------------
uniform mat4  u_viewProjection;   // combined VP matrix
uniform mat4  u_model;            // per-batch model matrix
uniform vec3  u_cameraPos;        // world-space camera position
uniform float u_time;             // animation clock (seconds)
uniform float u_fogStart;         // fog near distance
uniform float u_fogEnd;           // fog far distance

// -----------------------------------------------------------------------
// Outputs → fragment shader
// -----------------------------------------------------------------------
out vec3  v_worldPos;
out vec3  v_color;
out float v_health;
out float v_selected;
out vec2  v_texCoord;
out float v_fogFactor;
out float v_distToCamera;

// -----------------------------------------------------------------------
// Main
// -----------------------------------------------------------------------
void main() {
    vec4 worldPos4 = u_model * vec4(a_position, 1.0);
    v_worldPos     = worldPos4.xyz;

    // Distance to camera for fog-of-war attenuation
    float dist       = length(u_cameraPos - v_worldPos);
    v_distToCamera   = dist;
    v_fogFactor      = clamp((u_fogEnd - dist) / (u_fogEnd - u_fogStart), 0.0, 1.0);

    // Subtle idle bob animation for living units
    vec3 animPos = worldPos4.xyz;
    if (a_health > 0.0) {
        animPos.y += sin(u_time * 2.0 + a_position.x * 0.5) * 0.05 * a_health;
    }

    v_color    = a_color;
    v_health   = a_health;
    v_selected = a_selected;
    v_texCoord = a_texCoord;

    gl_Position = u_viewProjection * vec4(animPos, 1.0);
    gl_PointSize = max(4.0, 12.0 * a_health);   // dying units shrink
}
