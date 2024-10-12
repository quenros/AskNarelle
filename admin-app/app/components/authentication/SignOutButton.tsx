import { msalInstance } from "@/app/_app";
import { useRouter } from "next/navigation";

export default function SignOutButton() {

  const router = useRouter()
  const handleLogout = (logoutType: string) => {
    if (logoutType === "popup") {
      msalInstance.logoutPopup().then(() => {
        router.push("/")
      });
    } else if (logoutType === "redirect") {
      msalInstance.logoutRedirect().catch((e) => {
        console.error(`logoutRedirect failed: ${e}`);
      });
    }
  };

  return (
      <button
        className="bg-[#FF5C5C] hover:bg-[#FF8A8A] text-white font-semibold font-nunito rounded px-4 py-2 transition duration-300 transform hover:scale-105"
        onClick={() => handleLogout("popup")}
      >
        Log Out
      </button>
  );
}
