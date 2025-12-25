import { serve } from "https://deno.land/std@0.224.0/http/server.ts";

serve(async () => {
  console.log("cron triggered");

  const LINE_ACCESS_TOKEN = Deno.env.get("LINE_ACCESS_TOKEN");
  const LINE_USER_ID = Deno.env.get("LINE_USER_ID");
  const serviceRoleKey = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY");

  if (!LINE_ACCESS_TOKEN || !LINE_USER_ID) {
    return new Response("Missing LINE env vars", { status: 500 });
  }

  // 今は固定メッセージ（cron動作確認用）
  await fetch("https://api.line.me/v2/bot/message/push", {
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
          text: "cron からの自動通知です ⏰",
        },
      ],
    }),
  });

  return new Response("ok");
});
