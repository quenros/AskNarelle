import React from "react";
import Link from "next/link";
import { Button, Result } from "antd";

const NotFoundPage: React.FC = () => {
  return (
    <div
      style={{
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
        minHeight: "100vh",
        backgroundColor: "#f5f5f5", // Light gray background to match Ant Design theme
      }}
    >
      <Result
        status="404"
        title="404"
        subTitle="Oops! The page you are looking for does not exist."
        extra={
          <Link href="/">
            <Button type="primary" size="large">
              Back Home
            </Button>
          </Link>
        }
      />
    </div>
  );
};

export default NotFoundPage;