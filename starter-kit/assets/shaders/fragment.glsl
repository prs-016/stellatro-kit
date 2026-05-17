#version 330 core

uniform sampler2D tex;
in vec2 uvs;

// 1. You must declare your own output variable
out vec4 f_color; 

void main() {
    // 2. Use 'texture()' instead of 'texture2D()'
    // 3. Assign the result to your custom 'f_color' instead of 'gl_FragColor'
    f_color = texture(tex, uvs);
}