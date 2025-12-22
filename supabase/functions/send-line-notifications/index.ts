import { serve } from "https://deno.land/std@0.224.0/http/server.ts";

serve(async () => {
  // Supabase の環境変数から取得
  const LINE_ACCESS_TOKEN = Deno.env.get("LINE_CHANNEL_ACCESS_TOKEN");
  const LINE_USER_ID = Deno.env.get("LINE_USER_ID");

  if (!LINE_ACCESS_TOKEN || !LINE_USER_ID) {
    return new Response("Missing LINE env vars", { status: 500 });
  }

  // LINE Push API
  const res = await fetch("https://api.line.me/v2/bot/message/push", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "Authorization": `Bearer ${LINE_ACCESS_TOKEN}`,
    },
    body: JSON.stringify({
      to: LINE_USER_ID,
      messages: [
        {
          type: "text",
          text: "習慣の時間です ⏰（テスト通知）",
        },
      ],
    }),
  });

  return new Response(
    JSON.stringify({ success: res.ok }),
    {
      headers: { "Content-Type": "application/json" },
    }
  );
});
