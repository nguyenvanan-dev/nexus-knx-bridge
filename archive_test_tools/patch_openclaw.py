import os

files = [
    "/home/an/.openclaw/npm/projects/openclaw-zalouser-23f4f34fca/node_modules/@openclaw/zalouser/dist/monitor-DxOj93Pa.js"
]

voice_func = """
async function tryHandleVoiceCommand(params) {
	const chatId = String(params.message?.chat?.id ?? "");
	const senderId = String(params.message?.from?.id ?? "unknown");
	const voiceUrl = params.message?.voice_url || params.message?.content?.url || params.message?.voice_file_url;
	if (!chatId || !voiceUrl) return true;

	await sendZaloLongTextForDocKnx(
		params.token,
		chatId,
		"Đang nghe và giải mã giọng nói...",
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
		if (data && data.message) {
			replyText = String(data.message);
		} else if (response.ok) {
			replyText = JSON.stringify(data, null, 2);
		} else {
			replyText = "Lỗi xử lý Voice: HTTP " + String(response.status) + "\\n" + responseText;
		}

		await sendZaloLongTextForDocKnx(params.token, chatId, replyText, params.fetcher, params.statusSink);
	} catch (err) {
		await sendZaloLongTextForDocKnx(
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
				rawWebhook: params.rawWebhook,
				token,
				account,
				config,
				runtime,
				core,
				message,
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

print("Patch applied successfully to all files.")
