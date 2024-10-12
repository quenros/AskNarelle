import React, { useState, useEffect, useCallback } from 'react';
import SignOutButton from './authentication/SignOutButton';
import { PublicClientApplication } from "@azure/msal-browser";
import { msalConfig } from "@/authConfig";
import { AuthenticatedTemplate, UnauthenticatedTemplate } from "@azure/msal-react";
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { RiMenu3Fill } from "react-icons/ri";
import { IoCloseCircleOutline } from "react-icons/io5";

export const msalInstance = new PublicClientApplication(msalConfig);

const Navigation: React.FC = () => {
  const pathname = usePathname();
  const [activeLink, setActiveLink] = useState(pathname);
  const [underlineRef, setUnderlineRef] = useState<HTMLDivElement | null>(null);
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    setActiveLink(pathname);
  }, [pathname]);

  useEffect(() => {
    let activeLinkExtract = '';
    const updateUnderlinePosition = () => {
      if (activeLink.startsWith('/knowledgebase_management')) {
        activeLinkExtract = '/knowledgebase_management';
      } else if (activeLink.startsWith('/activity_log')) {
        activeLinkExtract = '/activity_log'; // Handle activity log path
      } else {
        activeLinkExtract = activeLink; // Handle other paths
      }
      const activeElement = document.querySelector<HTMLAnchorElement>(`a[href="${activeLinkExtract}"]`);
      if (activeElement && underlineRef) {
        const reducedWidth = activeElement.offsetWidth - 45; // Adjust 45 to your desired reduction
        underlineRef.style.width = `${Math.max(reducedWidth, 0)}px`; // Ensure width is non-negative
        underlineRef.style.left = `${activeElement.offsetLeft}px`;
      }
    };

    updateUnderlinePosition();
  }, [activeLink, underlineRef]);

  const handleNav = () => {
    setMenuOpen(!menuOpen);
  };

  // Determine if the current path is under /knowledgebase_management/
  const isKnowledgeBaseActive = activeLink.startsWith('/knowledgebase_management');
  const isActivityLogActive = activeLink.startsWith('/activity_log')

  return (
    <nav className='flex justify-center border-b-2 shadow-md fixed top-0 w-full h-[8vh] p-5 z-50 bg-white'>
      <AuthenticatedTemplate>
        <div className="container mx-auto flex items-center justify-between">
          <div>
            <a className="text-[#2C3463] text-xl font-bold font-nunito">AskNarelle</a>
          </div>
          <div className="space-x-5 relative hidden sm:flex">
            <Link href="/" className={`${activeLink === '/' ? 'text-[#2C3463]' : ''} font-nunito font-semibold mt-2`}>Dashboard</Link>
            <Link
              href="/knowledgebase_management"
              className={`${isKnowledgeBaseActive ? 'text-[#2C3463]' : ''} font-nunito font-semibold mt-2`}
            >
              Knowledge Base
            </Link>
            <Link
              href="/activity_log"
              className={`${isActivityLogActive ? 'text-[#2C3463]' : ''} font-nunito font-semibold mt-2`}
            >
              Activity Log
            </Link>

            <div
              ref={setUnderlineRef}
              className="absolute bottom-2 h-1 left-0 w-10 bg-[#2C3463] transition-all duration-300 ease-in-out"
            />
            <SignOutButton />
          </div>
          <div className='sm:hidden cursor-pointer pl-24' onClick={handleNav}>
            <RiMenu3Fill size={20} color='#2C3463'/>
          </div>
        </div>
        <div className={
          menuOpen ? "fixed left-0 top-0 w-[55%] sm:hidden h-screen bg-[#ecf0f3] p-10 ease-in duration-500":
          "fixed left-[-100%] top-0 p-10 h-screen ease-in duration-500"
        }>
          <div className='flex w-full justify-end'>
            <div onClick={handleNav} className='cursor-pointer'>
              <IoCloseCircleOutline size={25}/>
            </div>
          </div>
          <div className='flex-col py-4'>
            <ul>
              <Link href='/'>
                <li
                  onClick={() => setMenuOpen(false)}
                  className='py-4 cursor-pointer hover:text-[#2C3463] relative group'
                >
                  Dashboard
                  <span
                    className="absolute bottom-3 left-0 w-0 h-[2px] bg-[#2C3463] transition-all duration-300 group-hover:w-[20%]"
                  />
                </li>
              </Link>
              <Link href='/knowledgebase_management'>
                <li
                  onClick={() => setMenuOpen(false)}
                  className={`py-4 cursor-pointer relative group ${isKnowledgeBaseActive ? 'text-[#2C3463]' : ''}`}
                >
                  Knowledge Base
                  <span
                    className={`absolute bottom-3 left-0 h-[2px] bg-[#2C3463] transition-all duration-300 ${isKnowledgeBaseActive ? 'w-[20%]' : 'w-0'} group-hover:w-[20%]`}
                  />
                </li>
              </Link>
              <Link href='/activity_log'>
                 <li 
                 onClick = {() => setMenuOpen(false)}
                 className={`py-4 cursor-pointer relative group ${isActivityLogActive ? 'text-[#2C3463]' : ''}`}
                 >
                    Activity Log 
                    <span
                    className={`absolute bottom-3 left-0 h-[2px] bg-[#2C3463] transition-all duration-300 ${isActivityLogActive ? 'w-[20%]' : 'w-0'} group-hover:w-[20%]`}
                  />
                 </li>
              </Link>
              <li onClick={() => setMenuOpen(false)} className='py-4'>
                <SignOutButton />
              </li>
            </ul>
          </div>
        </div>
      </AuthenticatedTemplate>
      <UnauthenticatedTemplate>
        <div className="container mx-auto flex items-center justify-between">
          <div>
            <a className="text-[#2C3463] text-xl font-bold font-nunito">AskNarelle</a>
          </div>
        </div>
      </UnauthenticatedTemplate>
    </nav>
  );
};

export default Navigation;


