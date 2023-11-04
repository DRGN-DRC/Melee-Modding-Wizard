// #version 150
#version 330 core

// Define constants
#define RENDER_NORMAL 0
#define RENDER_DIM 1

// GXAlphaOp
#define ALPHA_OP_AND 0
#define ALPHA_OP_OR 1
#define ALPHA_OP_XOR 2
#define ALPHA_OP_XNOR 3

// GXCompare
#define COMP_NEVER 0
#define COMP_LESS 1
#define COMP_EQUAL 2
#define COMP_LEQUAL 3
#define COMP_GREATER 4
#define COMP_NEQUAL 5
#define COMP_GEQUAL 6
#define COMP_ALWAYS 7

// Texture flags
#define COORD_UV 0
#define COORD_REFLECTION 1
#define COORD_HIGHLIGHT 2
#define COORD_SHADOW 3
#define COORD_TOON 4
#define COORD_GRADATION 5
#define LIGHTMAP_DIFFUSE 1
#define LIGHTMAP_SPECULAR 2
#define LIGHTMAP_AMBIENT 4
#define LIGHTMAP_EXT 8
#define LIGHTMAP_SHADOW 16
#define COLORMAP_NONE 0
#define COLORMAP_ALPHA_MASK 1
#define COLORMAP_RGB_MASK 2
#define COLORMAP_BLEND 3
#define COLORMAP_MODULATE 4
#define COLORMAP_REPLACE 5
#define COLORMAP_PASS 6
#define COLORMAP_ADD 7
#define COLORMAP_SUB 8
#define ALPHAMAP_NONE 0
#define ALPHAMAP_ALPHA_MASK 1
#define ALPHAMAP_BLEND 2
#define ALPHAMAP_MODULATE 3
#define ALPHAMAP_REPLACE 4
#define ALPHAMAP_PASS 5
#define ALPHAMAP_ADD 6
#define ALPHAMAP_SUB 7

// TexGenSource
#define GX_TG_POS 0
#define GX_TG_NRM 1
#define GX_TG_BINRM 2
#define GX_TG_TANGENT 3
#define GX_TG_TEX0 4
#define GX_TG_TEX1 5
#define GX_TG_TEX2 6
#define GX_TG_TEX3 7
#define GX_TG_TEX4 8
#define GX_TG_TEX5 9
#define GX_TG_TEX6 10
#define GX_TG_TEX7 11
#define GX_TG_TEXCOORD0 12
#define GX_TG_TEXCOORD1 13
#define GX_TG_TEXCOORD2 14
#define GX_TG_TEXCOORD3 15
#define GX_TG_TEXCOORD4 16
#define GX_TG_TEXCOORD5 17
#define GX_TG_TEXCOORD6 18
#define GX_TG_COLOR0 19
#define GX_TG_COLOR1 20

// Temp hardcoded lighting values (todo: get from light objects)
vec3 finalAmbiLight = vec3(0.6);
vec3 finalDiffLight = vec3(0.6);
vec3 finalSpecLight = vec3(0.7);
//vec3 finalSpecLight = vec3(0.8, 0.8, 0.8);

// Define inputs from the program
uniform int renderState;

// Texture input variables
uniform int texGenSource;
uniform bool enableTextures;
uniform sampler2D texture0;
uniform int textureFlags;
uniform float textureBlending;
uniform mat4 textureMatrix;

// Set material colors
uniform bool useVertexColors;
uniform vec4 ambientColor;
uniform vec4 diffuseColor;
uniform vec4 specularColor;
uniform float shininess;
uniform float materialAlpha;

// For final fragment Alpha testing
uniform int alphaOp;
uniform int alphaComp0;
uniform int alphaComp1;
uniform float alphaRef0;
uniform float alphaRef1;

// Get inputs from the vertex shader
in vec4 vertColor;
in vec2 textureCoords;

// Final output color
out vec4 fragColor;


// Generate and return texture coordinates 
// based on the coordinate type and source.
vec2 getTextureCoords()
{
	vec2 coords;
	int texCoordType = (textureFlags & 5); // Mask out first 5 bits

	switch (texCoordType)
	{
		case COORD_UV: // The usual case
			//coords = gl_TexCoord[0].st;
			coords = textureCoords;
			break;

		// case COORD_REFLECTION:
		// 	// Return sphere coordinates
		// 	vec3 viewNormal = mat3(sphereMatrix) * normal;
		// 	coords = viewNormal.xy * 0.5 + 0.5;
		// 	coords.y = 1 - coords.y;
		// 	return coords;
		// 	//break;

		// case COORD_TOON:
		// 	vec3 V = normalize(vertPosition - cameraPos);
		// 	float lambert = clamp(dot(normal, V) + 0.4, 0, 1);
		// 	return vec2(lambert, lambert);
		// 	//break;

		// todo; missing the following:
		// COORD_HIGHLIGHT
		// COORD_SHADOW
		// COORD_GRADATION

		default: // Failsafe
			coords = vec2(0, 0);
			break;
	}

	// Check texture generation source
	// switch (texGenSource)
	// {

	// }

	// Apply transformations from the texture matrix (TObj values)
	vec4 transformedCoords = textureMatrix * vec4(coords.s, coords.t, 0, 1);

	return transformedCoords.st;
}

// Combines texture color and alpha with material color
// (passColor, which may be diffuse/ambient/etc.).
vec4 applyTextureOperations(vec4 passColor, vec4 texColor)
{
	// Check TObj flags for color and alpha operations
	int colorOP = (int(textureFlags >> 16) & 0xF);
	int alphaOP = (int(textureFlags >> 20) & 0xF);

	// Apply color manipulation
	switch (colorOP)
	{
		case COLORMAP_NONE:
			break;
		case COLORMAP_ALPHA_MASK:
			if(texColor.a != 0)
				passColor.rgb = mix(passColor.rgb, texColor.rgb, texColor.a);
			break;
		case COLORMAP_RGB_MASK:
			{
				//TODO: I don't know what this is
				if(texColor.r != 0)
					passColor.r = texColor.r;
				else
					passColor.r = 0;
				if(texColor.g != 0)
					passColor.g = texColor.g;
				else
					passColor.g = 0;
				if(texColor.b != 0)
					passColor.b = texColor.b;
				else
					passColor.b = 0;
			}
			break;
		case COLORMAP_BLEND:
			passColor.rgb = mix(passColor.rgb, texColor.rgb, textureBlending);
			break;
		case COLORMAP_MODULATE:
			passColor.rgb *= texColor.rgb;
			break;
		case COLORMAP_REPLACE:
			passColor.rgb = texColor.rgb;
			break;
		case COLORMAP_PASS:
			break;
		case COLORMAP_ADD:
			passColor.rgb += texColor.rgb * texColor.a;
			break;
		case COLORMAP_SUB:
			passColor.rgb -= texColor.rgb * texColor.a;
			break;
	}

	// Apply alpha channel manipulation
	switch (alphaOP)
	{
		case ALPHAMAP_NONE:
			break;
		case ALPHAMAP_ALPHA_MASK:
			// TODO: alpha mask with alpha?
			break;
		case ALPHAMAP_BLEND:
			passColor.a = mix(passColor.a, texColor.a, textureBlending);
			break;
		case ALPHAMAP_MODULATE:
			passColor.a *= texColor.a;
			break;
		case ALPHAMAP_REPLACE:
			passColor.a = texColor.a;
			break;
		case ALPHAMAP_PASS:
			break;
		case ALPHAMAP_ADD:
			passColor.a += texColor.a;
			break;
		case ALPHAMAP_SUB:
			passColor.a -= texColor.a;
			break;
	}

	return passColor;
}

// Gets a color from the texture for this fragment
// and combines it with material lighting according
// to texture flags.
vec4 applyTexture()
{
	// Get the initial texture color
	vec2 textureCoords = getTextureCoords();
	vec4 textureColor = texture(texture0, textureCoords).rgba;
	
	// Skip influence of material colors if using vertex colors
	if (useVertexColors) {
		// Combine with vertex colors
		// if (useVertexColors) // HSDRaw method
		// {
		// textureColor.rgb *= gl_Color.rgb * gl_Color.aaa;
		// textureColor.a *= gl_Color.a;
		// }
		// if (useVertexColors)
		textureColor *= vertColor;
		return textureColor;
	}

	// Check texture color/alpha combination flags
	int lightingFlags = (int(textureFlags >> 4) & 0x11);

	// Apply material lighting for enabled aspects
	vec4 texAmbience;
	if (bool(lightingFlags & LIGHTMAP_AMBIENT)) {
		texAmbience = applyTextureOperations(ambientColor, textureColor);
	} else {
		texAmbience = ambientColor;
	}
	vec4 diffusedColor = vec4(diffuseColor.rgb, materialAlpha * diffuseColor.a);
	vec4 texDiffuse;
	if (bool(lightingFlags & LIGHTMAP_DIFFUSE)) {
		texDiffuse = applyTextureOperations(diffusedColor, textureColor);
	} else {
		texDiffuse = diffusedColor;
	}
	// vec4 texSpecular;
	// if (lightingFlags & LIGHTMAP_SPECULAR)
	// 	texSpecular = applyTextureOperations(specularColor, textureColor);
	// else
	// 	texSpecular = specularColor;
	
	// Combine the material lighting and texture color
	vec4 surfaceColor = vec4(1.0, 1.0, 1.0, texDiffuse.a);
	surfaceColor.rgb = texAmbience.rgb * texDiffuse.rgb * finalAmbiLight +
						texDiffuse.rgb * finalDiffLight;// +
						// texSpecular.rgb * finalSpecLight;

	//vec4 texExt;
	// if (lightingFlags & LIGHTMAP_EXT) {
	// 	surfaceColor = applyTextureOperations(surfaceColor, textureColor);
	// } 
	// else {
	// 	texExt = ambientColor;
	// }

	return surfaceColor;
}

vec4 applyMaterialColor()
{
	// Combine the material lighting and texture color
	// vec3 finalAmbiLight = vec3(0.9);
	// vec3 finalDiffLight = vec3(0.9, 0.9, 0.9);
	vec3 materialColor = ambientColor.rgb * diffuseColor.rgb * finalAmbiLight +
						diffuseColor.rgb * finalDiffLight;// +
						//specularPass.rgb * finalSpecLight;

	return vec4(materialColor, materialAlpha * diffuseColor.a);
}


// Ensures the given alpha component is within bounds
// when compared to the reference alpha value.
// Values are from the pixel-processing struct.
bool alphaIsGood(int comp, float ref, float fragmentAlpha)
{
	return 
	(
		// COMP_NEVER (enum 0) will return false by default
		(comp == COMP_ALWAYS) || // 7
		(comp == COMP_LESS && fragmentAlpha < ref) || // 1
		(comp == COMP_EQUAL && fragmentAlpha == ref) || // 2
		(comp == COMP_LEQUAL && fragmentAlpha <= ref) || // 3
		(comp == COMP_GREATER && fragmentAlpha > ref) || // 4
		(comp == COMP_NEQUAL && fragmentAlpha != ref) || // 5
		(comp == COMP_GEQUAL && fragmentAlpha >= ref) // 6
	);
}

// Returns true if the fragment fails the test and should be discarded.
// This is used when pixel-processing is enabled; bounds and comparison
// methods for this test are taken from the PE struct.
bool failsAlphaTest(float fragmentAlpha)
{
	// Sanity check
	if (fragmentAlpha < 0.0)
		return true;

	// Skip check if no alpha operation is set
	if (alphaOp == -1)
		return false;
	
	// Compare the given alpha value to two reference values
	bool pass0 = alphaIsGood(alphaComp0, alphaRef0, fragmentAlpha);
	bool pass1 = alphaIsGood(alphaComp1, alphaRef1, fragmentAlpha);

	switch(alphaOp)
	{
		case ALPHA_OP_AND:
			return !(pass0 && pass1);
		case ALPHA_OP_OR:
			return !(pass0 || pass1);
		case ALPHA_OP_XOR:
			return !(pass0 != pass1);
		case ALPHA_OP_XNOR:
			return !(pass0 == pass1);
	}

	// Failsafe; should have returned above
	return true;
}

// Algorithm from Chapter 16 of OpenGL Shading Language
// Adjusts colors for percieved brightness.
vec3 adjustSaturation(vec3 inputColor, float amount)
{
	const vec3 lumaCoefficients = vec3(0.2125, 0.7154, 0.0721);
	vec3 intensity = vec3(dot(inputColor, lumaCoefficients));
	return mix(intensity, inputColor, amount);
}

// The main processing function, to determine a single output color for the current fragment.
void main()
{
	// Start off with a color from a texture, material, or vertex
	if (enableTextures) {
		// Get the texture color and combine with material or vertex colors
		fragColor = applyTexture();

	} else if (useVertexColors) {
		// Start with vertex colors only
		fragColor = vertColor;
		//fragColor = vec4(0, 1.0, 0, 0.5); // green

	} else {
		// Combine material lighting aspects
		vec3 materialColor = ambientColor.rgb * diffuseColor.rgb * finalAmbiLight +
							diffuseColor.rgb * finalDiffLight;// +
							//specularPass.rgb * finalSpecLight;
		fragColor = vec4(materialColor, materialAlpha * diffuseColor.a);
	}

	// if (alphaOp == -1) {
	// 	fragColor = vec4(1.0, 1.0, 0, 0.5); // yellow
	// 	return;
	// }
	// if (alphaOp == 0) {
	// 	fragColor = vec4(1.0, 0, 0, 0.5); // red
	// 	return;
	// }
	// if (alphaOp == 1) {
	// 	fragColor = vec4(0, 1.0, 0, 0.5); // green
	// 	return;
	// }
	// if (alphaOp == 2) {
	// 	fragColor = vec4(0, 0, 1.0, 0.5); // blue
	// 	return;
	// }

	// Discard fragments which fail the pixel-processing alpha test
	if (failsAlphaTest(fragColor.a))
		discard;
		// fragColor = vec4(1.0, 0, 0, 0.5); // red

	// Reduce saturation and brightness for model parts that should be obscured
	if (renderState == RENDER_DIM)
	{
		fragColor.rgb = adjustSaturation(fragColor.rgb, .3);
		fragColor *= vec4(.45, .45, .45, 1.0);
	}

	//gl_FragColor = fragColor;
	
	// if (alphaOp == -1)
	// 	fragColor = vec4(1.0, 0, 0, 0.5); // red
	// else
	// fragColor = vec4(0, 1.0, 0, 0.5); // green

	// Saturation adjustment
	//fragColor.rgb = adjustSaturation(fragColor.rgb, .9);
}