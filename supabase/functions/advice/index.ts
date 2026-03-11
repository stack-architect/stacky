import "jsr:@supabase/functions-js/edge-runtime.d.ts";
import {
  corsHeaders,
  generateEmbedding,
  searchDocuments,
  generateAnswer,
  getSupabaseClient,
  getOpenRouterKey,
} from "../_shared/lib.ts";

const STACK_ADVISOR_PROMPT = `You are an expert Stack Advisor for Next.js, Vercel, and Supabase. Provide clear, actionable architectural guidance with practical examples. Keep responses focused and concise.`;

Deno.serve(async (req) => {
  // Handle CORS
  if (req.method === "OPTIONS") {
    return new Response("ok", { headers: corsHeaders });
  }

  try {
    const { query } = await req.json();

    if (!query) {
      return new Response(
        JSON.stringify({ error: "Query is required" }),
        { status: 400, headers: { ...corsHeaders, "Content-Type": "application/json" } }
      );
    }

    console.log("Stack advice query:", query);

    const supabase = getSupabaseClient();
    const openrouterKey = getOpenRouterKey();

    // Generate embedding
    console.log("Generating embedding...");
    const embedding = await generateEmbedding(query);

    // Search technical documentation (exclude stackarchitect business content)
    console.log("Searching technical documentation...");
    const documents = await searchDocuments(supabase, embedding, 5, null);
    console.log("Found documents:", documents.length);

    // Generate answer with Stack Advisor prompt
    console.log("Generating architectural advice...");
    const answer = await generateAnswer(query, documents, STACK_ADVISOR_PROMPT, openrouterKey);

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
