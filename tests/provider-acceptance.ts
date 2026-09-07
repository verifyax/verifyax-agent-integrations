import {Type, type FunctionDeclaration, type Schema, type Tool} from "@google/genai";
import artifact from "../gemini/verifyax-functions.json" with {type: "json"};

type ArtifactSchema = {
  type: string;
  description?: string;
  format?: string;
  nullable?: boolean;
  enum?: string[];
  items?: ArtifactSchema;
  properties?: Record<string, ArtifactSchema>;
  required?: string[];
};

function toSdkSchema(input: ArtifactSchema, location: string): Schema {
  if (!Object.values(Type).includes(input.type as Type)) {
    throw new Error(`${location}: unsupported Gemini schema type ${input.type}`);
  }
  const {items, properties, ...scalarFields} = input;
  const schema: Schema = {
    ...scalarFields,
    type: input.type as Type,
  };
  if (items) {
    schema.items = toSdkSchema(items, `${location}[]`);
  }
  if (properties) {
    schema.properties = Object.fromEntries(
      Object.entries(properties).map(([name, value]) => [
        name,
        toSdkSchema(value, `${location}.${name}`),
      ]),
    );
  }
  return schema;
}

const functionDeclarations: FunctionDeclaration[] = artifact.map((declaration) => ({
  name: declaration.name,
  description: declaration.description,
  parameters: declaration.parameters
    ? toSdkSchema(declaration.parameters as unknown as ArtifactSchema, declaration.name)
    : undefined,
}));

const tools: Tool[] = [{functionDeclarations}];

if (tools[0].functionDeclarations?.length !== artifact.length) {
  throw new Error("Gemini SDK rejected one or more generated function declarations");
}
