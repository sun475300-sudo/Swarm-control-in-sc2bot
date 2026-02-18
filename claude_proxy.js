const express = require('express');
const bodyParser = require('body-parser');
const cors = require('cors');
const fetch = require('node-fetch');
const crypto = require('crypto');
const path = require('path');
require('dotenv').config({ path: path.join(__dirname, '.env.jarvis') });

const app = express();
const PORT = 8765; // Proxy Port

app.use(cors());
app.use(bodyParser.json());
app.use((req, res, next) => {
    res.header('Content-Type', 'application/json; charset=utf-8');
    next();
});

const SESSION_KEY = process.env.CLAUDE_SESSION_KEY;

// --- Claude Web Client Logic ---
async function queryClaudeWeb(prompt) {
    // 1. Get Organization ID
    let orgId = null;
    try {
        const orgRes = await fetch('https://claude.ai/api/organizations', {
            headers: {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
                'Cookie': `sessionKey=${SESSION_KEY}`,
                'Content-Type': 'application/json'
            }
        });

        if (!orgRes.ok) throw new Error(`Org Fetch Failed: ${orgRes.status}`);
        const orgs = await orgRes.json();
        orgId = orgs[0].uuid;
    } catch (e) {
        console.error('Claude Org Error:', e);
        return null;
    }

    // 2. Start Conversation & Send Message
    try {
        const chatRes = await fetch(`https://claude.ai/api/organizations/${orgId}/chat_conversations`, {
            method: 'POST',
            headers: {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
                'Cookie': `sessionKey=${SESSION_KEY}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                uuid: crypto.randomUUID(),
                name: ""
            })
        });
        const chat = await chatRes.json();
        const chatId = chat.uuid;

        const msgRes = await fetch(`https://claude.ai/api/organizations/${orgId}/chat_conversations/${chatId}/completion`, {
            method: 'POST',
            headers: {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
                'Cookie': `sessionKey=${SESSION_KEY}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                prompt: prompt,
                timezone: "Asia/Seoul",
                model: "claude-3-opus-20240229" // Use Opus (Pro)
            })
        });

        const text = await msgRes.text();
        const lines = text.split('\n');
        let fullResponse = "";
        for (const line of lines) {
            if (line.startsWith('data: ')) {
                try {
                    const data = JSON.parse(line.slice(6));
                    if (data.completion) fullResponse += data.completion;
                } catch (e) { }
            }
        }
        return fullResponse;

    } catch (e) {
        console.error('Claude Chat Error:', e);
        return null;
    }
}

// --- Sanitize Claude response (strip tool-use XML, artifacts, etc.) ---
function sanitizeResponse(text) {
    if (!text) return text;

    let cleaned = text;

    // Remove <function_calls>...</function_calls> blocks (closed tags)
    cleaned = cleaned.replace(/<function_calls>[\s\S]*?<\/function_calls>/g, '');

    // Remove unclosed <function_calls> that run to end of text (streaming cutoff)
    cleaned = cleaned.replace(/<function_calls>[\s\S]*$/g, '');

    // Remove <*>...</*> blocks (Anthropic internal tags)
    cleaned = cleaned.replace(/<[^>]*>[\s\S]*?<\/antml:[^>]*>/g, '');

    // Remove <artifact>...</artifact> blocks
    cleaned = cleaned.replace(/<artifact[\s\S]*?<\/artifact>/g, '');

    // Remove <search_quality_reflection> blocks
    cleaned = cleaned.replace(/<search_quality_reflection>[\s\S]*?<\/search_quality_reflection>/g, '');

    // Remove <thinking>...</thinking> blocks
    cleaned = cleaned.replace(/<thinking>[\s\S]*?<\/thinking>/g, '');

    // Remove <response>...</response> wrapper (keep inner content)
    cleaned = cleaned.replace(/<\/?response>/g, '');

    // Remove standalone <invoke>, <parameter> tags that might remain
    cleaned = cleaned.replace(/<\/?invoke[^>]*>/g, '');
    cleaned = cleaned.replace(/<\/?parameter[^>]*>/g, '');

    // Clean up excessive whitespace left by removals
    cleaned = cleaned.replace(/\n{3,}/g, '\n\n').trim();

    return cleaned || '(응답을 처리할 수 없었습니다)';
}

// --- OpenAI Compatible Endpoint ---
app.post('/v1/chat/completions', async (req, res) => {
    console.log('📨 Request from OpenClaw (OpenAI Compat)');
    // ... (keep existing logic if needed, or we can just focus on /chat)
    // For now, I'll keep it but adding /chat is the priority.
    try {
        const messages = req.body.messages;
        const lastMessage = messages[messages.length - 1].content;
        console.log('🗣️ User:', lastMessage);

        const rawResponse = await queryClaudeWeb(lastMessage);
        if (!rawResponse) throw new Error("Claude Web Error");
        const claudeResponse = sanitizeResponse(rawResponse);

        console.log('🤖 Claude:', claudeResponse.substring(0, 50) + '...');
        res.json({
            id: "chatcmpl-" + Date.now(),
            object: "chat.completion",
            created: Math.floor(Date.now() / 1000),
            model: "claude-pro-web",
            choices: [{
                index: 0,
                message: { role: "assistant", content: claudeResponse },
                finish_reason: "stop"
            }],
            usage: { prompt_tokens: 0, completion_tokens: 0, total_tokens: 0 }
        });
    } catch (e) {
        console.error("Endpoint Error:", e);
        res.status(500).json({ error: e.message });
    }
});

// --- JARVIS Custom Endpoint ---
app.post('/chat', async (req, res) => {
    console.log('📨 Request from JARVIS Bot (/chat)');
    try {
        // defined in discord_voice_chat_jarvis.js:342 -> body: { message, user, images }
        const userMessage = req.body.message;
        const userId = req.body.user;
        // const images = req.body.images; // logic for images if needed in future

        if (!userMessage) {
            return res.status(400).json({ error: "Message is required" });
        }

        console.log(`🗣️ User (${userId}):`, userMessage.substring(0, 100));

        // Use the same Claude Web query function
        const rawResponse = await queryClaudeWeb(userMessage);

        if (!rawResponse) {
            throw new Error("Failed to get response from Claude");
        }

        const claudeResponse = sanitizeResponse(rawResponse);
        console.log('🤖 Claude:', claudeResponse.substring(0, 50) + '...');

        // Return format expected by discord bot: { reply: ... }
        res.json({ reply: claudeResponse });

    } catch (e) {
        console.error("Endpoint Error:", e);
        res.status(500).json({ error: "Internal Server Error", reply: "죄송해요, 처리 중에 문제가 발생했어요." });
    }
});

app.listen(PORT, () => {
    console.log(`✅ Claude Proxy Server running at http://localhost:${PORT}`);
    console.log('🔌 Waiting for OpenClaw connection...');
});
