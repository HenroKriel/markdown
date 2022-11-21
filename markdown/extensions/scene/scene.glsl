uniform float time;
#define PI 3.14159
varying vec2 glpos;
uniform vec2 resolution;

mat4 transform;

struct Intersection {
    bool valid;
    vec3 pos;
    vec3 norm;
    float t;
};

struct Ray {
    vec3 p;
    vec3 d;
};

Intersection intersect(Ray ray) {
    Intersection ret;
    ret.valid = false;

    vec4 p = inverse(transform)*vec4(ray.p, 1.0);
    vec4 d = vec4(inverse(mat3(transform))*ray.d, 0.0);
    
    float total_dist = 0.0;
    const float MAX_DIST = 100.0;
    const float MIN_HIT_DIST = 0.01;
    const int NUM_ITER = 32;

    for(int i = 0; i < NUM_ITER; i++) {
        vec4 sect = p + d*total_dist;

        SHAPE_input _input = SHAPE_input(vec3(sect));
        float dist = SHAPE(_input).d;

        if(dist < MIN_HIT_DIST) {
            ret.valid = true;
            //needs differentiation
            vec3 norm = grad_SHAPE(_input);

            ret.pos = (transform*sect).xyz;
            //precompute inverse function
            ret.norm = (transpose(inverse(mat3(transform)))*norm.xyz);
            ret.norm = normalize(ret.norm);
            
            return ret;
        }

        if(total_dist > MAX_DIST)
            return ret;

        total_dist += dist;
    }
}

void main() {
    //TRANSFORM
    transform = ret;
    vec2 coord = glpos/min(resolution.x, resolution.y);
    gl_FragColor = vec4(0.0, 0.0, 0.0, 1.0);
    vec3 eye = vec3(0.0, 0.0, -1.0);
    Ray ray = Ray(eye, vec3(coord, 0.0) - eye);
    Intersection sect = intersect(ray);
    if(sect.valid) {
        vec3 color = vec3(1.0);

        //need a standard for position and normal inputs
        phong_input _input;
        _input.k_a = vec3(0.1, 0.1, 0.1);
        _input.k_d = vec3(0.0, 1.0, 0.0);
        _input.k_s = vec3(0.5, 0.5, 0.5);
        _input.A[0] = vec3(0.1, 0.1, 0.1);
        _input.dim_0 = 1;
        _input.alpha = 1.5;
        _input.P[0] = vec3(0.0, time, -1.0);
        _input.p = sect.pos;
        _input.D[0] = vec3(0.5, 0.5, 0.5);
        _input.S[0] = vec3(0.1, 0.1, 0.1);
        _input.N_hat = sect.norm;
        _input.V_hat = eye - sect.pos;
        color = phong(_input).I_p;

        gl_FragColor = vec4(color, 1.0);
        //gl_FragColor = vec4(0.0, 1.0, 0.0, 1.0);
    }
}