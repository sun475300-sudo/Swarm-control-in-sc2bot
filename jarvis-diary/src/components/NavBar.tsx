"use client";

import Link from "next/link";

export default function NavBar() {
    return (
        <nav className="fixed top-0 left-0 right-0 z-50 px-6 py-4">
            <div className="max-w-7xl mx-auto flex items-center justify-between glass px-6 py-3 rounded-full">
                <Link href="/" className="flex items-center space-x-2 group">
                    <div className="w-8 h-8 bg-primary rounded-lg flex items-center justify-center font-bold text-primary-foreground group-hover:rotate-12 transition-transform">
                        J
                    </div>
                    <span className="font-display font-bold text-xl tracking-tight text-gradient">
                        JARVIS Diary
                    </span>
                </Link>
                <div className="hidden md:flex items-center space-x-8 text-sm font-medium">
                    <Link href="#timeline" className="hover:text-primary transition-colors">프로젝트 타임라인</Link>
                    <Link href="#status" className="hover:text-primary transition-colors">현재 상태</Link>
                    <div className="px-4 py-1.5 bg-primary text-primary-foreground rounded-full font-bold cursor-pointer hover:opacity-90 transition-opacity">
                        사장님 모드
                    </div>
                </div>
            </div>
        </nav>
    );
}
