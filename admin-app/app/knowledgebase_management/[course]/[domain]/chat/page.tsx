"use client";

import React, { useState, useRef, useEffect } from "react";
import { useParams, useRouter, useSearchParams } from "next/navigation";
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
  const params = useParams();
  const course = decodeURIComponent(String(params?.course || ""));
  const domain = decodeURIComponent(String(params?.domain || ""));

  const searchParams = useSearchParams();
  const videoId = searchParams.get("id") || "";
  const videoName = searchParams.get("name"); 

  const isCourseChat = !videoId;
  const chatTitle = isCourseChat ? `Course Chat: ${course}` : (videoName || "Video Chat");

  const [loading, setLoading] = useState(false);
  const [inputText, setInputText] = useState("");
  const [uiMessages, setUiMessages] = useState<ChatMessage[]>([]);
  const [apiHistory, setApiHistory] = useState<ChatHistory[]>([]);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };
  
  useEffect(() => {
    scrollToBottom();
  }, [uiMessages]);

  const handleSend = async () => {
    if (!inputText.trim()) return;

    const userMsg = inputText;
    setInputText("");
    setLoading(true);

    setUiMessages((prev) => [...prev, { role: "user", content: userMsg }]);
    
    try {
      let url = "";
      let payload: any = {
        previous_messages: apiHistory,
        message: userMsg,
        video_ids: [] 
      };

      if (isCourseChat) {
        // UPDATED: Pass course code in the URL path
        url = `http://localhost:5000/api/chat/${encodeURIComponent(course)}`;
      } else {
        // Single Video Endpoint (You might want to update this too to follow the pattern, 
        // but for now keeping it as is or redirecting to the main one with specific video_ids)
        // If you want to use the unified endpoint for single videos too:
        url = `http://localhost:5000/api/chat/${encodeURIComponent(course)}`;
        payload.video_ids = [videoId];
      }

      const res = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!res.ok) throw new Error("Failed to fetch response");

      const data = await res.json();
      const botResponse = data.answer || "Sorry, I couldn't understand that.";

      setUiMessages((prev) => [...prev, { role: "assistant", content: botResponse }]);
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
      <Header
        style={{
          background: "#fff",
          borderBottom: "1px solid #f0f0f0",
          padding: "0 24px",
          display: "flex",
          alignItems: "center",
          height: 64,
          zIndex: 10,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
          <Button
            icon={<ArrowLeftOutlined />}
            onClick={() => router.back()}
            type="text"
            style={{ fontSize: 16 }}
          />
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
        </div>
      </Header>

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
          {uiMessages.length === 0 && (
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