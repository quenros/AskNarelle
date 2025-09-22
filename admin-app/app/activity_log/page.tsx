"use client";

import React, { useEffect, useMemo, useState } from "react";
import { msalConfig } from "@/authConfig";
import { PublicClientApplication } from "@azure/msal-browser";
import withAuth from "../components/authentication/WithAuth";
import ForbiddenPage from "../components/authentication/403";

import {
  Table,
  Input,
  Select,
  DatePicker,
  Space,
  Typography,
  Tag,
  Alert,
  Spin,
  Empty,
  Button,
} from "antd";
import type { ColumnsType } from "antd/es/table";
import dayjs, { Dayjs } from "dayjs";
import isBetween from "dayjs/plugin/isBetween";
import { SearchOutlined, ReloadOutlined } from "@ant-design/icons";

dayjs.extend(isBetween);
const { RangePicker } = DatePicker;
const { Text } = Typography;

interface Activity {
  _id: string;
  username: string;
  course_name: string;
  domain: string;
  file: string;
  action: string;
  date_str: string; // "YYYY-MM-DD"
  time_str: string;
}

const msalInstance = new PublicClientApplication(msalConfig);

function ActivityLog(): JSX.Element {
  const accounts = msalInstance.getAllAccounts();
  const viewer = accounts[0]?.username;

  const [authorised, setAuthorised] = useState(true);
  const [activities, setActivities] = useState<Activity[]>([]);
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // Filters
  const [qUser, setQUser] = useState("");
  const [qCourse, setQCourse] = useState("");
  const [qDomain, setQDomain] = useState("");
  const [qFile, setQFile] = useState("");
  const [actionType, setActionType] = useState<string>("");
  const [range, setRange] = useState<[Dayjs | null, Dayjs | null] | null>(null);

  useEffect(() => {
    if (!viewer) return;
    const ac = new AbortController();
    setLoading(true);
    setErrorMsg(null);

    fetch(
      `http://localhost:5000/activities/${encodeURIComponent(
        viewer
      )}/viewactivities`,
      { signal: ac.signal }
    )
      .then((res) => {
        if (res.status === 403) {
          setAuthorised(false);
          return null;
        }
        if (!res.ok) throw new Error("Failed to fetch activities");
        return res.json();
      })
      .then((data: Activity[] | null) => {
        if (data) setActivities(data);
      })
      .catch((err) => {
        if (err.name !== "AbortError") {
          setErrorMsg("Error fetching activities");
          // eslint-disable-next-line no-console
          console.error(err);
        }
      })
      .finally(() => setLoading(false));

    return () => ac.abort();
  }, [viewer]);

  const normalize = (s?: string) => (s ? s.toLowerCase() : "");

  const filtered = useMemo(() => {
    const [start, end] = range || [null, null];

    return (activities || []).filter((a) => {
      const inUser = normalize(a.username).includes(normalize(qUser));
      const inCourse = normalize(a.course_name).includes(normalize(qCourse));
      const inDomain = normalize(a.domain).includes(normalize(qDomain));
      const inFile = normalize(a.file).includes(normalize(qFile));
      const inAction = !actionType || a.action === actionType;

      const day = dayjs(a.date_str, "YYYY-MM-DD"); // treat as local day
      const inRange =
        !start ||
        !end ||
        day.isBetween(start.startOf("day"), end.endOf("day"), "day", "[]");

      return inUser && inCourse && inDomain && inFile && inAction && inRange;
    });
  }, [activities, qUser, qCourse, qDomain, qFile, actionType, range]);

  const uniqueActions = useMemo(
    () => Array.from(new Set(activities.map((a) => a.action))).sort(),
    [activities]
  );

  const actionColor: Record<string, string> = {
    "Uploaded File": "green",
    "Deleted Domain": "red",
    "Deleted File": "red",
    "Blob Deletion": "red",
    "Moved to vector store": "blue",
    "Domain Creation": "cyan",
  };

  const columns: ColumnsType<Activity> = [
    {
      title: "When",
      dataIndex: "date_str",
      key: "when",
      width: 190,
      align: "center",
      fixed: "left",
      sorter: (a, b) =>
        dayjs(`${a.date_str} ${a.time_str}`).valueOf() -
        dayjs(`${b.date_str} ${b.time_str}`).valueOf(),
      render: (_, r) => (
        <Space direction="vertical" size={0}>
          <Text>{r.date_str}</Text>
          <Text type="secondary" style={{ fontSize: 12 }}>
            {r.time_str}
          </Text>
        </Space>
      ),
    },
    {
      title: "User",
      dataIndex: "username",
      key: "username",
      align: "center",
      width: 220,
      ellipsis: true,
      sorter: (a, b) => a.username.localeCompare(b.username),
      render: (v: string) => <Text>{v}</Text>,
    },
    {
      title: "Course",
      dataIndex: "course_name",
      key: "course_name",
      align: "center",
      width: 200,
      ellipsis: true,
      sorter: (a, b) => a.course_name.localeCompare(b.course_name),
    },
    {
      title: "Category",
      dataIndex: "domain",
      key: "domain",
      align: "center",
      width: 180,
      ellipsis: true,
      sorter: (a, b) => a.domain.localeCompare(b.domain),
    },
    {
      title: "File",
      dataIndex: "file",
      key: "file",
      align: "center",
      ellipsis: true,
      sorter: (a, b) => a.file.localeCompare(b.file),
      render: (v: string) =>
        v && v !== "null" ? <Text code>{v}</Text> : <Text type="secondary">—</Text>,
    },
    {
      title: "Action",
      dataIndex: "action",
      key: "action",
      align: "center",
      width: 220,
      filters: uniqueActions.map((a) => ({ text: a, value: a })),
      onFilter: (val, rec) => rec.action === val,
      render: (v: string) => <Tag color={actionColor[v] || "default"}>{v}</Tag>,
    },
  ];

  if (!authorised) return <ForbiddenPage />;

  return (
    <main className="flex flex-col min-h-screen pt-24 px-6 sm:px-10">
      <div className="mb-4">
        <Space size="middle" wrap>
          <Input
            allowClear
            prefix={<SearchOutlined />}
            placeholder="Filter by user"
            style={{ width: 220 }}
            value={qUser}
            onChange={(e) => setQUser(e.target.value)}
          />
          <Input
            allowClear
            prefix={<SearchOutlined />}
            placeholder="Filter by course"
            style={{ width: 220 }}
            value={qCourse}
            onChange={(e) => setQCourse(e.target.value)}
          />
          <Input
            allowClear
            prefix={<SearchOutlined />}
            placeholder="Filter by category"
            style={{ width: 200 }}
            value={qDomain}
            onChange={(e) => setQDomain(e.target.value)}
          />
          <Input
            allowClear
            prefix={<SearchOutlined />}
            placeholder="Filter by file name"
            style={{ width: 260 }}
            value={qFile}
            onChange={(e) => setQFile(e.target.value)}
          />
          <Select
            allowClear
            placeholder="Action"
            style={{ width: 220 }}
            value={actionType || undefined}
            onChange={(v) => setActionType(v || "")}
            options={uniqueActions.map((a) => ({ label: a, value: a }))}
          />
          <RangePicker
            value={range as any}
            onChange={(vals) => setRange(vals as any)}
            allowEmpty={[true, true]}
          />
          {(qUser || qCourse || qDomain || qFile || actionType || (range && (range[0] || range[1]))) && (
            <Button
              icon={<ReloadOutlined />}
              onClick={() => {
                setQUser("");
                setQCourse("");
                setQDomain("");
                setQFile("");
                setActionType("");
                setRange(null);
              }}
            >
              Clear
            </Button>
          )}
          <Text type="secondary" style={{ marginLeft: 8 }}>
            Showing {filtered.length} of {activities.length}
          </Text>
        </Space>
      </div>

      {errorMsg && (
        <Alert
          type="error"
          showIcon
          message="Error"
          description={errorMsg}
          style={{ marginBottom: 12 }}
        />
      )}

      {loading ? (
        <div className="flex items-center justify-center h-64">
          <Spin />
        </div>
      ) : (
        <Table<Activity>
          rowKey="_id"
          columns={columns}
          dataSource={filtered}
          size="middle"
          bordered
          sticky
          pagination={{ pageSize: 10, showSizeChanger: true }}
          scroll={{ x: 900 }}
          locale={{
            emptyText: <Empty description="No activity found" />,
          }}
        />
      )}
    </main>
  );
}

export default withAuth(ActivityLog);
