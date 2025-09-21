import React, { useEffect, useMemo, useState } from "react";
import {
  Modal,
  List,
  Avatar,
  Typography,
  Button,
  Popconfirm,
  Spin,
  Alert,
  Input,
  Space,
  Tag,
  message,
  Empty,
} from "antd";
import { UserOutlined, DeleteOutlined } from "@ant-design/icons";

interface PopupProps {
  onClose: () => void;
  courseName: string;
}

const ManageAccessPopup: React.FC<PopupProps> = ({ onClose, courseName }) => {
  const [open] = useState(true);
  const [users, setUsers] = useState<string[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [errorMessage, setErrorMessage] = useState<string>("");
  const [search, setSearch] = useState<string>("");
  const [deleting, setDeleting] = useState<string | null>(null);

  useEffect(() => {
    const load = async () => {
      try {
        setLoading(true);
        const resp = await fetch(`http://localhost:5000/manageaccess/${courseName}`);
        if (!resp.ok) throw new Error("Failed to fetch users");
        const data: string[] = await resp.json();
        setUsers(data || []);
        setErrorMessage("");
      } catch (e: any) {
        setErrorMessage(e?.message ?? "Error fetching users");
      } finally {
        setLoading(false);
      }
    };
    load();
  }, [courseName]);

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return users;
    return users.filter((u) => u.toLowerCase().includes(q));
  }, [users, search]);

  const handleDeleteUser = async (user: string) => {
    try {
      setDeleting(user);
      const resp = await fetch("http://localhost:5000/manageaccess/deleteUser", {
        method: "DELETE",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ collectionName: courseName, username: user }),
      });

      if (!resp.ok && resp.status !== 201) {
        const errText = `${resp.status} ${resp.statusText}`;
        throw new Error(errText || "Failed to remove user");
      }

      setUsers((prev) => prev.filter((u) => u !== user));
      message.success(`Removed access for ${user}`);
    } catch (e: any) {
      message.error(e?.message ?? "Error removing user");
    } finally {
      setDeleting(null);
    }
  };

  return (
    <Modal
      open={open}
      title={
        <Space align="center">
          <Typography.Text strong>People with access</Typography.Text>
          <Tag color="blue">{courseName}</Tag>
        </Space>
      }
      onCancel={loading || deleting ? undefined : onClose}
      maskClosable={!(loading || !!deleting)}
      closable={!(loading || !!deleting)}
      destroyOnClose
      width={560}
      footer={[
        <Button key="close" onClick={onClose} disabled={loading || !!deleting}>
          Close
        </Button>,
      ]}
    >
      <Space direction="vertical" style={{ width: "100%" }} size="middle">
        <Input
          placeholder="Search users (email)"
          allowClear
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          disabled={loading}
        />

        {errorMessage && (
          <Alert type="error" showIcon message="Error" description={errorMessage} />
        )}

        <List
          loading={loading}
          dataSource={filtered}
          locale={{
            emptyText: loading ? (
              <div style={{ textAlign: "center", padding: 24 }}>
                <Spin />
              </div>
            ) : (
              <Empty description="No users found" />
            ),
          }}
          renderItem={(user) => (
            <List.Item
              actions={[
                <Popconfirm
                  key="remove"
                  title="Remove access?"
                  description={`This will revoke ${user}'s access to ${courseName}.`}
                  okText="Remove"
                  okButtonProps={{ danger: true, loading: deleting === user }}
                  onConfirm={() => handleDeleteUser(user)}
                  disabled={!!deleting}
                >
                  <Button
                    danger
                    icon={<DeleteOutlined />}
                    loading={deleting === user}
                    disabled={!!deleting}
                  >
                    Remove
                  </Button>
                </Popconfirm>,
              ]}
            >
              <List.Item.Meta
                avatar={<Avatar icon={<UserOutlined />} />}
                title={<Typography.Text>{user}</Typography.Text>}
                description="Has access to this course"
              />
            </List.Item>
          )}
        />
      </Space>
    </Modal>
  );
};

export default ManageAccessPopup;
