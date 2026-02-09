/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    return [
      // --- Existing Routes ---
      {
        source: '/api/:path*',
        destination: 'http://127.0.0.1:5000/api/:path*',
      },
      {
        source: '/chats/:path*',
        destination: 'http://127.0.0.1:5000/chats/:path*',
      },
      {
        source: '/vi/:path*',
        destination: 'http://127.0.0.1:5000/vi/:path*',
      },
      {
        source: '/createindex',
        destination: 'http://127.0.0.1:5000/createindex',
      },
      {
        source: '/vectorstore',
        destination: 'http://127.0.0.1:5000/vectorstore',
      },
      {
        source: '/movetovectorstore',
        destination: 'http://127.0.0.1:5000/movetovectorstore',
      },
      {
        source: '/updatemovement',
        destination: 'http://127.0.0.1:5000/updatemovement',
      },
      {
        source: '/manageaccess/:path*',
        destination: 'http://127.0.0.1:5000/manageaccess/:path*',
      },
      {
        source: '/invite',
        destination: 'http://127.0.0.1:5000/invite',
      },
      {
        source: '/activities/:path*',
        destination: 'http://127.0.0.1:5000/activities/:path*',
      },
      {
        source: '/chat/:path*',
        destination: 'http://127.0.0.1:5000/chat/:path*',
      },
    ]
  },
};

export default nextConfig;