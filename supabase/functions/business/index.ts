import "jsr:@supabase/functions-js/edge-runtime.d.ts";
import {
  corsHeaders,
  generateEmbedding,
  searchDocuments,
  generateAnswer,
  getSupabaseClient,
  getOpenRouterKey,
} from "../_shared/lib.ts";

const BUSINESS_PROMPT = `You are a helpful assistant for StackArchitect. Keep responses brief and conversational - answer directly without lengthy explanations.`;

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

    console.log("Business query:", query);

    const supabase = getSupabaseClient();
    const openrouterKey = getOpenRouterKey();

    // Generate embedding
    console.log("Generating embedding...");
    const embedding = await generateEmbedding(query);

    // Search StackArchitect documents only
    console.log("Searching StackArchitect content...");
    const documents = await searchDocuments(supabase, embedding, 5, 'stackarchitect');
    console.log("Found documents:", documents.length);

    // Generate answer with business prompt
    console.log("Generating answer...");
    const answer = await generateAnswer(query, documents, BUSINESS_PROMPT, openrouterKey);

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
