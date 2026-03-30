#version 300 es
precision mediump float;

// SC2 Zerg AI Bot — Battlefield Fragment Shader
// Renders units with health-based colour, fog-of-war darkening,
// and selection highlight ring.

// -----------------------------------------------------------------------
// Inputs from vertex shader
// -----------------------------------------------------------------------
in vec3  v_worldPos;
in vec3  v_color;
in float v_health;
in float v_selected;
in vec2  v_texCoord;
in float v_fogFactor;
in float v_distToCamera;

// -----------------------------------------------------------------------
// Uniforms
// -----------------------------------------------------------------------
uniform sampler2D u_sprite;          // unit sprite atlas
uniform vec3      u_fogColor;        // fog-of-war tint (dark grey)
uniform float     u_time;            // animation clock
uniform float     u_fogVisibility;   // 0 = full fog, 1 = full visibility

// -----------------------------------------------------------------------
// Output
// -----------------------------------------------------------------------
out vec4 fragColor;

// -----------------------------------------------------------------------
// Health colour: green (full) → yellow (50%) → red (low)
// -----------------------------------------------------------------------
vec3 healthColor(float h) {
    if (h > 0.5) {
        return mix(vec3(1.0, 1.0, 0.0), vec3(0.0, 1.0, 0.0), (h - 0.5) * 2.0);
    } else {
        return mix(vec3(1.0, 0.0, 0.0), vec3(1.0, 1.0, 0.0), h * 2.0);
    }
}

// -----------------------------------------------------------------------
// Selection pulse ring
// -----------------------------------------------------------------------
float selectionRing(vec2 uv, float time) {
    float dist  = length(uv - vec2(0.5));
    float pulse = 0.45 + 0.04 * sin(time * 6.0);
    float ring  = smoothstep(pulse - 0.02, pulse, dist) *
                  smoothstep(pulse + 0.02, pulse, dist);
    return ring;
}

// -----------------------------------------------------------------------
// Main
// -----------------------------------------------------------------------
void main() {
    // Base sprite colour
    vec4 spriteColor = texture(u_sprite, v_texCoord);
    if (spriteColor.a < 0.1) discard;

    // Tint by faction colour
    vec3 tinted = spriteColor.rgb * v_color;

    // Overlay health bar tint (subtle blend)
    vec3 hColor  = healthColor(v_health);
    vec3 unitCol = mix(tinted, hColor * tinted, 0.35);

    // Selection highlight
    float ring  = selectionRing(v_texCoord, u_time) * v_selected;
    unitCol     = mix(unitCol, vec3(0.2, 0.9, 1.0), ring * 0.8);

    // Fog of war
    float fog     = v_fogFactor * u_fogVisibility;
    vec3 finalCol = mix(u_fogColor, unitCol, fog);

    // Dead units fade to grey
    finalCol = mix(vec3(dot(finalCol, vec3(0.299, 0.587, 0.114))), finalCol,
                   smoothstep(0.0, 0.1, v_health));

    fragColor = vec4(finalCol, spriteColor.a);
}
