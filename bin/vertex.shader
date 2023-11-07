#version 330 core

// Recieve vertex attributes from the render engine
layout (location = 0) in vec3 vertexPosition;
layout (location = 1) in vec4 vertexColorAttr;
layout (location = 2) in vec2 textureCoordsAttr;
//layout (location = 3) in vec2 normals;

// Recieve components for the MVP matrix (Model*View*Projection Matrix)
uniform mat4 projectionViewMatrix;

// Output vertex position (in clip space)
out vec4 vertColor;
out vec2 textureCoords;

void main() {
	// Transform the vertex position by the MVP matrices (vertex coords already in model space)
	//mat4 identityMatrix = mat4( 1.0f ); // Shorthand to construct identity matrix
	gl_Position = projectionViewMatrix * vec4(vertexPosition, 1.0);

	// Pass other vertex attributes on to the fragment shader
	vertColor = vertexColorAttr;
	textureCoords = textureCoordsAttr;
}