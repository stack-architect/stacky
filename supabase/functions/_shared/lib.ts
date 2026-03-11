import { createClient } from "jsr:@supabase/supabase-js@2";
import CONFIG from "../../../config.json" with { type: "json" };

export const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
};

// Lazy-loaded AI session
let aiSession: any = null;

export async function getAISession() {
  if (!aiSession) {
    console.log("Initializing Supabase AI session:", CONFIG.embedding.model_js);
    // @ts-ignore - Supabase AI is available in edge runtime
    aiSession = new Supabase.ai.Session(CONFIG.embedding.model_js);
    console.log("AI session initialized");
  }
  return aiSession;
}

export async function generateEmbedding(text: string): Promise<number[]> {
  const session = await getAISession();
  const embedding = await session.run(text, {
    mean_pool: true,
    normalize: true,
  });

  if (embedding.length !== CONFIG.embedding.dimensions) {
    throw new Error(
      `Generated embedding has ${embedding.length} dimensions, expected ${CONFIG.embedding.dimensions}`
    );
  }

  return embedding;
}

export async function searchDocuments(
  supabase: any,
  embedding: number[],
  limit = 5,
  sourceFilter: string | null = null
) {
  const { data, error } = await supabase.rpc("match_documents", {
    query_embedding: embedding,
    match_count: limit,
    filter_source: sourceFilter,
  });

  if (error) throw error;
  return data;
}

export async function generateAnswer(
  query: string,
  contexts: any[],
  systemPrompt: string,
  apiKey: string
) {
  const contextText = contexts
    .map((doc, i) => `[${i + 1}] ${doc.title}\n${doc.content}`)
    .join("\n\n");

  const prompt = `${systemPrompt}

Context:
${contextText}

Question: ${query}`;

  const response = await fetch("https://openrouter.ai/api/v1/chat/completions", {
    method: "POST",
    headers: {
      "Authorization": `Bearer ${apiKey}`,
      "Content-Type": "application/json",
      "HTTP-Referer": "https://stacky.stackarchitect.io",
      "X-Title": "Stacky",
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

export function getSupabaseClient() {
  const supabaseUrl = Deno.env.get("SUPABASE_URL") ?? "";
  const supabaseKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY") ?? "";
  return createClient(supabaseUrl, supabaseKey);
}

export function getOpenRouterKey(): string {
  const key = Deno.env.get("OPENROUTER_API_KEY");
  if (!key) {
    throw new Error("OPENROUTER_API_KEY not set");
  }
  return key;
}
