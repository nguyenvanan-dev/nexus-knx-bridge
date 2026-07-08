import os

files = [
    "/home/an/.openclaw/npm/projects/openclaw-zalo-762456265a/node_modules/@openclaw/zalo/dist/monitor-BCnfAVr4.js"
]

voice_func = """
async function sendZaloTextOnly(token, chatId, textLocal, fetcher, statusSink) {
    try {
        await sendMessage(token, {
            chat_id: chatId,
            text: textLocal
        }, fetcher);
        if (statusSink) statusSink({ lastOutboundAt: Date.now() });
    } catch (e) {
        console.error("sendZaloTextOnly err", e);
    }
}

async function tryHandleVoiceCommand(params) {
	const chatId = String(params.message?.chat?.id ?? "");
	const senderId = String(params.message?.from?.id ?? "unknown");
	const voiceUrl = params.message?.voice_url || params.message?.content?.url || params.message?.voice_file_url;
	if (!chatId || !voiceUrl) return true;

	await sendZaloTextOnly(
		params.token,
		chatId,
		"🎙️ Đang nghe và giải mã giọng nói qua Groq Whisper...",
		params.fetcher,
		params.statusSink
	);

	try {
		const response = await fetch("http://127.0.0.1:5055/agent/voice", {
			method: "POST",
			headers: { "Content-Type": "application/json" },
			body: JSON.stringify({
				user_id: "zalo_" + senderId,
				voice_url: voiceUrl
			})
		});

		const responseText = await response.text();
		let data;
		try {
			data = JSON.parse(responseText);
		} catch {
			data = { message: responseText };
		}

		let replyText;
		if (data && data.transcribed_text) {
			replyText = "🗣️ Bạn nói: " + String(data.transcribed_text) + "\\n\\n⏳ Đang xử lý...";
		} else if (data && data.message) {
			replyText = String(data.message);
		} else {
			replyText = "Lỗi xử lý Voice: HTTP " + String(response.status) + "\\n" + responseText;
		}

		await sendZaloTextOnly(params.token, chatId, replyText, params.fetcher, params.statusSink);
        
        if (data && data.transcribed_text) {
            // Re-inject as a text message into the pipeline
            params.message.text = data.transcribed_text;
            await handleTextMessage({
				message: params.message,
				token: params.token,
                account: params.account,
                config: params.config,
                runtime: params.runtime,
                core: params.core,
                mediaMaxMb: params.mediaMaxMb,
                canHostMedia: params.canHostMedia,
                webhookUrl: params.webhookUrl,
                webhookPath: params.webhookPath,
                statusSink: params.statusSink,
                fetcher: params.fetcher
			});
        }
	} catch (err) {
		await sendZaloTextOnly(
			params.token,
			chatId,
			"Lỗi kết nối bộ giải mã Voice: " + String(err?.message ?? err),
			params.fetcher,
			params.statusSink
		);
	}

	return true;
}
"""

case_block = """	switch (event_name) {
		case "message.voice.received":
			await tryHandleVoiceCommand({
				update,
				token,
				account,
				config,
				runtime,
				core,
				message,
				mediaMaxMb: params.mediaMaxMb,
                canHostMedia: params.canHostMedia,
                webhookUrl: params.webhookUrl,
                webhookPath: params.webhookPath,
				statusSink,
				fetcher
			});
			break;"""

for filepath in files:
    with open(filepath, "r") as f:
        content = f.read()
        
    if "tryHandleVoiceCommand" not in content:
        content = content.replace("async function processUpdate(params) {", voice_func + "\nasync function processUpdate(params) {")

    if 'case "message.voice.received":' not in content:
        content = content.replace("\tswitch (event_name) {\n", case_block + "\n")

    with open(filepath, "w") as f:
        f.write(content)

print("Patch applied successfully to OA plugin.")
