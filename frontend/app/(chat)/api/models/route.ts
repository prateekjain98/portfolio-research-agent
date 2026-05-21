export async function GET() {
  const headers = {
    "Cache-Control": "public, max-age=86400, s-maxage=86400",
  };

  // Return a single model — the frontend uses backend proxy anyway.
  // This prevents the UI from crashing on activeModels[0] being undefined.
  return Response.json(
    {
      capabilities: {},
      models: [
        {
          id: "mistral:latest",
          name: "Mistral",
          provider: "ollama",
          description: "Local model via Ollama",
        },
      ],
    },
    { headers }
  );
}
