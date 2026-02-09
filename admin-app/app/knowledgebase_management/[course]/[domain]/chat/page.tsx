"use client";

import React, { useState, useRef, useEffect } from "react";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { PublicClientApplication } from "@azure/msal-browser"; // Import MSAL
import { msalConfig } from "@/authConfig"; // Import config
import {
  Layout,
  Input,
  Button,
  List,
  Typography,
  Avatar,
  Spin,
  Breadcrumb,
  message as antMessage,
  Empty,
} from "antd";
import {
  SendOutlined,
  UserOutlined,
  RobotOutlined,
  ArrowLeftOutlined,
} from "@ant-design/icons";

const { Header, Content, Footer } = Layout;
const { Text, Title } = Typography;

// Initialize MSAL instance
const msalInstance = new PublicClientApplication(msalConfig);

// --- Interfaces matching your Backend ---
interface ChatHistory {
  user_input: string;
  assistant_response: string;
}

interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

const ChatPage: React.FC = () => {
  const router = useRouter();
  
  // 1. Get Path Params (Course/Domain)
  const params = useParams();
  // Ensure we decode the params in case they are URL encoded
  const course = decodeURIComponent(String(params?.course || ""));
  const domain = decodeURIComponent(String(params?.domain || ""));

  // 2. Get Query Params (Video ID / Name)
  const searchParams = useSearchParams();
  const videoId = searchParams.get("id") || "";
  const videoName = searchParams.get("name"); 

  // 3. Get User ID from MSAL
  const accounts = msalInstance.getAllAccounts();
  const userId = accounts?.[0]?.username || "anonymous";

  // Determine Chat Mode
  const isCourseChat = !videoId;
  const chatTitle = isCourseChat ? `Course Chat: ${course}` : (videoName || "Video Chat");

  const [loading, setLoading] = useState(false);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [inputText, setInputText] = useState("");
  
  // UI State for the list
  const [uiMessages, setUiMessages] = useState<ChatMessage[]>([]);
  // API State for the history buffer
  const [apiHistory, setApiHistory] = useState<ChatHistory[]>([]);

  // Auto-scroll logic
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };
  
  useEffect(() => {
    scrollToBottom();
  }, [uiMessages]);

  // Fetch Chat History on Mount 
  useEffect(() => {
    const fetchHistory = async () => {
        if (!course || !userId || userId === "anonymous") return;
        
        setHistoryLoading(true);
        try {
            const res = await fetch(`/api/chat/history/${encodeURIComponent(course)}?user_id=${encodeURIComponent(userId)}`);
            if (res.ok) {
                const data = await res.json();
                const history = data.history || [];
                
                // 1. Format for UI
                const formattedUI: ChatMessage[] = history.map((msg: any) => ({
                    role: msg.role,
                    content: msg.content
                }));
                setUiMessages(formattedUI);

                // 2. Format for API Context (ChatHistory format)
                // We need to pair user/assistant messages for the ChatHistory object
                // This is a naive pairing assuming strict alternating order, which might not always hold
                // Ideally, the backend manages history now so we might not strictly need to send this full list back
                // if we are using session-based context.
                // But to keep compatibility with your ChatHelper's previous_messages logic:
                const pairedHistory: ChatHistory[] = [];
                for (let i = 0; i < history.length - 1; i += 2) {
                    if (history[i].role === 'user' && history[i+1].role === 'assistant') {
                        pairedHistory.push({
                            user_input: history[i].content,
                            assistant_response: history[i+1].content
                        });
                    }
                }
                setApiHistory(pairedHistory);
            }
        } catch (error) {
            console.error("Failed to load chat history:", error);
        } finally {
            setHistoryLoading(false);
        }
    };

    fetchHistory();
  }, [course, userId]);

  const handleSend = async () => {
    if (!inputText.trim()) return;

    // Safety check for video mode
    if (!isCourseChat && !videoId) {
        antMessage.error("Missing Video ID.");
        return;
    }

    const userMsg = inputText;
    setInputText("");
    setLoading(true);

    // 1. Optimistic UI Update
    setUiMessages((prev) => [...prev, { role: "user", content: userMsg }]);

    try {
      let url = "";
      // Construct payload based on your backend 'ChatRequestBody' model
      let payload: any = {
        previous_messages: apiHistory, 
        message: userMsg,
        user_id: userId, 
      };

      if (isCourseChat) {
        // Course Chat Endpoint
        url = `/api/chat/${encodeURIComponent(course)}`;
      } else {
        // Single Video Endpoint
        url = `/chat/${encodeURIComponent(videoId)}`;
        payload.course_code = course; 
        payload.user_id = userId;
      }

      const res = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!res.ok) throw new Error("Failed to fetch response");

      const data = await res.json();
      const botResponse = data.answer || "Sorry, I couldn't understand that.";

      // 4. Update UI with Bot Response
      setUiMessages((prev) => [...prev, { role: "assistant", content: botResponse }]);
      
      // 5. Update History
      setApiHistory((prev) => [
        ...prev,
        { user_input: userMsg, assistant_response: botResponse },
      ]);

    } catch (error) {
      console.error(error);
      antMessage.error("Error connecting to knowledge base.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Layout style={{ height: "100vh", background: "#fff" }}>
      {/* --- HEADER --- */}
      <Header
        style={{
          background: "#fff",
          borderBottom: "1px solid #f0f0f0",
          padding: "0 24px",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          height: 64,
          zIndex: 10,
        }}
      >
        <div style={{ display: "flex", flexDirection: "column", justifyContent: "center" }}>
          <Breadcrumb
            items={[
              { title: course },
              { title: domain },
              { title: isCourseChat ? "Course Chat" : "Video Chat" },
            ]}
            style={{ fontSize: 12, lineHeight: "20px" }}
          />
          <Title level={5} style={{ margin: 0, lineHeight: "24px" }}>
            {chatTitle}
          </Title>
        </div>
        <Button
          icon={<ArrowLeftOutlined />}
          onClick={() => router.push(`/knowledgebase_management/${encodeURIComponent(course)}/${encodeURIComponent(domain)}`)}
          type="text"
          style={{ fontSize: 16 }}
        />
      </Header>

      {/* --- CHAT CONTENT --- */}
      <Content
        style={{
          padding: "24px",
          overflowY: "auto",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
        }}
      >
        <div style={{ width: "100%", maxWidth: 800 }}>
          {/* Welcome Empty State */}
          {uiMessages.length === 0 && !historyLoading && (
            <div style={{ textAlign: "center", marginTop: 80, opacity: 0.6 }}>
              <div style={{ 
                  width: 80, height: 80, background: '#e6f7ff', borderRadius: '50%', 
                  margin: '0 auto 24px', display: 'flex', alignItems: 'center', justifyContent: 'center' 
              }}>
                <RobotOutlined style={{ fontSize: 40, color: "#1890ff" }} />
              </div>
              <Title level={3}>{isCourseChat ? "Course Knowledge Base" : "Video Knowledge Base"}</Title>
              <Text style={{ fontSize: 16 }}>
                {isCourseChat 
                    ? `Ask anything about the ${course} course materials.`
                    : `Ask questions specifically about ${videoName || "this video"}.`
                }
              </Text>
            </div>
          )}
          
          {historyLoading && (
             <div style={{ padding: "20px 0", textAlign: "center" }}>
               <Spin tip="Loading chat history..." />
             </div>
          )}

          {/* Message List */}
          <List
            itemLayout="horizontal"
            dataSource={uiMessages}
            split={false}
            renderItem={(item) => (
              <List.Item style={{ padding: "16px 0", border: 'none' }}>
                <List.Item.Meta
                  avatar={
                    <Avatar
                      size="large"
                      style={{
                        backgroundColor: item.role === "user" ? "#f5f5f5" : "#e6f7ff",
                        color: item.role === "user" ? "rgba(0,0,0,0.45)" : "#1890ff",
                        border: '1px solid #f0f0f0'
                      }}
                      icon={item.role === "user" ? <UserOutlined /> : <RobotOutlined />}
                    />
                  }
                  title={
                    <div style={{ marginBottom: 4 }}>
                        <Text strong>{item.role === "user" ? "You" : "Assistant"}</Text>
                    </div>
                  }
                  description={
                    <div style={{ 
                        color: 'rgba(0, 0, 0, 0.88)', 
                        fontSize: 15,
                        lineHeight: 1.6,
                        whiteSpace: "pre-wrap" 
                    }}>
                      {item.content}
                    </div>
                  }
                />
              </List.Item>
            )}
          />

          {loading && (
            <div style={{ padding: "20px 0", textAlign: "center" }}>
              <Spin tip="Analyzing knowledge base..." />
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>
      </Content>

      {/* --- FOOTER INPUT --- */}
      <Footer
        style={{
          background: "#fff",
          borderTop: "1px solid #f0f0f0",
          padding: "24px",
          display: "flex",
          justifyContent: "center",
        }}
      >
        <div style={{ width: "100%", maxWidth: 800, display: "flex", gap: 12 }}>
          <Input.TextArea
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            placeholder="Type your question..."
            autoSize={{ minRows: 1, maxRows: 6 }}
            style={{ 
                borderRadius: 12, 
                padding: '8px 12px',
                resize: 'none'
            }}
            onPressEnter={(e) => {
              if (!e.shiftKey) {
                e.preventDefault();
                handleSend();
              }
            }}
          />
          <Button
            type="primary"
            icon={<SendOutlined />}
            onClick={handleSend}
            loading={loading}
            style={{ height: 'auto', borderRadius: 12, padding: '0 20px' }}
          >
            Send
          </Button>
        </div>
      </Footer>
    </Layout>
  );
};

export default ChatPage;