import { msalInstance } from "../../_app";
import { loginRequest } from "@/authConfig";
import { MdEmail } from "react-icons/md";

export default function SignInButton() {
  const handleLogin = (loginType: string) => {
    if (loginType === "popup") {
      msalInstance.loginPopup(loginRequest).catch((e) => {
        console.error(`loginPopup failed: ${e}`);
      });
    } else if (loginType === "redirect") {
      msalInstance.loginRedirect(loginRequest).catch((e) => {
        console.error(`loginRedirect failed: ${e}`);
      });
    }
  };

  // loginRedirect does not work in NextJS v14.1.0
  return (
    <div className="bg-[#3F50AD] text-white px-4 py-2 rounded w-full cursor-pointer transition-transform duration-300 ease-in-out transform hover:scale-105 hover:bg-[#3C456C]" onClick={() => handleLogin("popup")}>
    <div className='flex justify-center font-nunito'>
    <MdEmail className='mr-2 size-6'/>
     Login with NTU Email
    </div>
    </div>
  );
}
