#version 330 core

// Recieve vertex attributes from the render engine
layout (location = 0) in vec3 vertexPosition;
layout (location = 1) in vec4 vertexColorAttr;
layout (location = 2) in vec2 textureCoordsAttr;
//layout (location = 3) in vec2 normals;

// Recieve components for the MVP matrix (Model*View*Projection Matrix)
uniform mat4 viewOrientation;
uniform mat4 viewTranslation;
uniform mat4 projectionMatrix;

// Output vertex position (in clip space)
out vec4 vertColor;
out vec2 textureCoords;

void main() {
	// Transform the vertex position by the MVP matrices
	//mat4 identityMatrix = mat4( 1.0f ); // Shorthand to construct identity matrix
	mat4 viewMatrix = viewOrientation * viewTranslation;
	gl_Position = projectionMatrix * viewMatrix * vec4(vertexPosition, 1.0);

	// Pass other vertex attributes on to the fragment shader
	vertColor = vertexColorAttr;
	textureCoords = textureCoordsAttr;
}