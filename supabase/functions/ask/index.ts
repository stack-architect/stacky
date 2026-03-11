import "jsr:@supabase/functions-js/edge-runtime.d.ts";
import { createClient } from "jsr:@supabase/supabase-js@2";
import CONFIG from "../../../config.json" with { type: "json" };

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
};

// Initialize Supabase AI session (lazy load)
let aiSession: any = null;
let configValidated = false;

async function validateConfig(supabase: any) {
  if (configValidated) return;

  try {
    const { data, error } = await supabase.rpc("get_embedding_config");

    if (error) {
      console.warn("Could not fetch embedding metadata:", error.message);
      return;
    }

    if (data && data.length > 0) {
      const dbConfig = data[0];
      if (dbConfig.model_js !== CONFIG.embedding.model_js) {
        console.error(
          `MODEL MISMATCH! Database: ${dbConfig.model_js}, Edge Function: ${CONFIG.embedding.model_js}`
        );
        throw new Error(
          `Embedding model mismatch. Database expects ${dbConfig.model_js}, but edge function uses ${CONFIG.embedding.model_js}`
        );
      }
      if (dbConfig.dimensions !== CONFIG.embedding.dimensions) {
        throw new Error(
          `Dimension mismatch. Database: ${dbConfig.dimensions}, Edge Function: ${CONFIG.embedding.dimensions}`
        );
      }
      console.log("✓ Embedding config validated:", dbConfig.model_js);
    }

    configValidated = true;
  } catch (err) {
    console.error("Config validation failed:", err);
    throw err;
  }
}

async function getAISession() {
  if (!aiSession) {
    console.log("Initializing Supabase AI session:", CONFIG.embedding.model_js);
    // @ts-ignore - Supabase AI is available in edge runtime
    aiSession = new Supabase.ai.Session(CONFIG.embedding.model_js);
    console.log("AI session initialized");
  }
  return aiSession;
}

// Generate embedding for query using Supabase AI
async function generateEmbedding(text: string): Promise<number[]> {
  const session = await getAISession();
  const embedding = await session.run(text, {
    mean_pool: true,
    normalize: true,
  });
  return embedding;
}

// Search similar documents
async function searchDocuments(supabase: any, embedding: number[], limit = 5) {
  const { data, error } = await supabase.rpc("match_documents", {
    query_embedding: embedding,
    match_count: limit,
  });

  if (error) throw error;
  return data;
}

// Generate answer using OpenRouter LLM
async function generateAnswer(query: string, contexts: any[], apiKey: string) {
  const contextText = contexts
    .map((doc, i) => `[${i + 1}] ${doc.title}\n${doc.content}`)
    .join("\n\n");

  const prompt = `You are a helpful assistant for developer documentation. Answer the user's question based on the provided documentation excerpts. Include specific details and code examples when available.

Documentation:
${contextText}

Question: ${query}

Answer concisely and accurately based on the documentation above. If the documentation doesn't contain relevant information, say so.`;

  const response = await fetch("https://openrouter.ai/api/v1/chat/completions", {
    method: "POST",
    headers: {
      "Authorization": `Bearer ${apiKey}`,
      "Content-Type": "application/json",
      "HTTP-Referer": "https://stacky.stackarchitect.io",
      "X-Title": "Stacky RAG",
    },
    body: JSON.stringify({
      model: "openrouter/free",
      messages: [
        { role: "user", content: prompt },
      ],
      temperature: 0.3,
    }),
  });

  if (!response.ok) {
    const error = await response.text();
    throw new Error(`OpenRouter API error: ${error}`);
  }

  const result = await response.json();
  return result.choices[0].message.content;
}

Deno.serve(async (req) => {
  // Handle CORS
  if (req.method === "OPTIONS") {
    return new Response("ok", { headers: corsHeaders });
  }

  try {
    // Get request body
    const { query } = await req.json();

    if (!query) {
      return new Response(
        JSON.stringify({ error: "Query is required" }),
        { status: 400, headers: { ...corsHeaders, "Content-Type": "application/json" } }
      );
    }

    console.log("Query:", query);

    // Get API keys from environment
    const openrouterKey = Deno.env.get("OPENROUTER_API_KEY");
    if (!openrouterKey) {
      throw new Error("OPENROUTER_API_KEY not set");
    }

    // Initialize Supabase client
    const supabaseUrl = Deno.env.get("SUPABASE_URL") ?? "";
    const supabaseKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY") ?? "";
    const supabase = createClient(supabaseUrl, supabaseKey);

    // Validate config on first request
    await validateConfig(supabase);

    // Step 1: Generate embedding for query
    console.log("Generating embedding...");
    const embedding = await generateEmbedding(query);
    console.log("Embedding generated:", embedding.length, "dimensions");

    // Validate dimensions
    if (embedding.length !== CONFIG.embedding.dimensions) {
      throw new Error(
        `Generated embedding has ${embedding.length} dimensions, expected ${CONFIG.embedding.dimensions}`
      );
    }

    // Step 2: Search similar documents
    console.log("Searching documents...");
    const documents = await searchDocuments(supabase, embedding, 5);
    console.log("Found documents:", documents.length);

    // Step 3: Generate answer with OpenRouter LLM
    console.log("Generating answer...");
    const answer = await generateAnswer(query, documents, openrouterKey);

    // Step 4: Return response
    const response = {
      answer,
      sources: documents.map((doc: any) => ({
        title: doc.title,
        url: doc.url,
        source: doc.source,
        similarity: doc.similarity,
      })),
    };

    return new Response(
      JSON.stringify(response),
      { headers: { ...corsHeaders, "Content-Type": "application/json" } }
    );

  } catch (error) {
    console.error("Error:", error);
    return new Response(
      JSON.stringify({ error: error.message }),
      { status: 500, headers: { ...corsHeaders, "Content-Type": "application/json" } }
    );
  }
});
