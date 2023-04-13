uniform float time;
varying vec2 glpos;
uniform vec2 resolution;
//INCLUDE UNIFORMS

struct Intersection {
    bool valid;
    vec3 pos;
    vec3 norm;
    float t;
    int material;
};

struct Ray {
    vec3 p;
    vec3 d;
};

Intersection intersect(Ray ray) {
    const float MAX_DIST = 100.0;
    const float MIN_HIT_DIST = 0.01;
    const int NUM_ITER = 32;

    vec4 p;
    vec4 d;
    float total_dist;

    Intersection best;
    best.valid = false;
    best.t = MAX_DIST;

    //INCLUDE INTERSECT

    return best;
}

void main() {
    vec2 coord = glpos/min(resolution.x, resolution.y);
    gl_FragColor = vec4(0.0, 0.0, 0.0, 1.0);
    vec3 eye = vec3(0.0, 0.0, -1.0);
    Ray ray = Ray(eye, normalize(vec3(coord, 0.0) - eye));
    Intersection sect = intersect(ray);
    if(sect.valid) {
        vec3 color = vec3(1.0);

        //INCLUDE MATERIALS

        gl_FragColor = vec4(color, 1.0);
        //gl_FragColor = vec4(0.0, 1.0, 0.0, 1.0);
    }
}