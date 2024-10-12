// components/SearchBar.tsx
import React from 'react'

const SearchBar: React.FC = () => {
  return (
    <div className="flex items-center border-2 border-gray-300 rounded-3xl p-2 shadow-sm mr-5">
      <svg className="w-7 h-7 text-gray-700" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
        <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-4.35-4.35M16.65 11a5.65 5.65 0 11-11.3 0 5.65 5.65 0 0111.3 0z"></path>
      </svg>
      <input
        type="text"
        placeholder="Search for Courses"
        className="ml-2 w-full bg-transparent focus:outline-none font-nunito"
      />
    </div>
  )
}

export default SearchBar
