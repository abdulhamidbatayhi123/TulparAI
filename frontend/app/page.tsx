"use client";

import { useState } from "react";
import { 
  Plus, UserCog, UploadCloud, PanelLeft, 
  BookOpen, Trash2, Search, Database, Brain, 
  ShieldCheck, Image as ImageIcon, Mic, Send, X,
  Thermometer, Pill, Moon, Flame, Zap
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";

export default function Home() {
  const [message, setMessage] = useState("");
  const [isSidebarOpen, setSidebarOpen] = useState(true);

  const setQuery = (query: string) => {
    setMessage(query);
  };

  return (
    <div className="flex h-screen overflow-hidden bg-background">
      {/* Sidebar */}
      <aside 
        className={`${isSidebarOpen ? "w-64" : "w-0"} transition-all duration-300 ease-in-out flex flex-col border-r border-border bg-card/30 backdrop-blur-md overflow-hidden shrink-0`}
      >
        {/* Logo */}
        <div className="h-16 flex items-center px-4 border-b border-border">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center text-primary-foreground font-bold">
              T
            </div>
            <h1 className="font-bold text-xl tracking-tight text-foreground whitespace-nowrap">
              Tulpar<span className="text-primary">AI</span>
            </h1>
          </div>
        </div>

        <div className="p-4 flex-1 overflow-y-auto space-y-6">
          <Button className="w-full justify-start gap-2" variant="outline">
            <Plus className="w-4 h-4" />
            New Conversation
          </Button>

          {/* Athlete Profile */}
          <div className="space-y-2">
            <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Athlete Profile</h3>
            <div className="p-3 rounded-lg bg-background border border-border">
              <div className="mb-2">
                <h4 className="text-sm font-semibold text-foreground">Guest Athlete</h4>
                <p className="text-xs text-muted-foreground">Personalize your training advice</p>
              </div>
              <Button variant="secondary" size="sm" className="w-full text-xs h-8 gap-2">
                <UserCog className="w-3.5 h-3.5" />
                Set Up Profile
              </Button>
            </div>
          </div>

          {/* Knowledge Base */}
          <div className="space-y-2">
            <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Knowledge Base</h3>
            <div className="flex gap-2">
              <div className="flex-1 p-2 rounded-lg bg-background border border-border flex flex-col items-center">
                <span className="text-lg font-bold text-foreground">56</span>
                <span className="text-[10px] text-muted-foreground uppercase">Sports Sci</span>
              </div>
              <div className="flex-1 p-2 rounded-lg bg-background border border-border flex flex-col items-center">
                <span className="text-lg font-bold text-foreground">0</span>
                <span className="text-[10px] text-muted-foreground uppercase">Your Docs</span>
              </div>
            </div>
            <Button variant="secondary" size="sm" className="w-full text-xs h-8 gap-2">
              <UploadCloud className="w-3.5 h-3.5" />
              Upload Document
            </Button>
          </div>

          {/* Recents */}
          <div className="space-y-2">
            <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Recents</h3>
            <div className="text-sm text-muted-foreground text-center py-4">
              No recent chats
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-border flex items-center gap-2 text-xs text-muted-foreground">
          <div className="w-2 h-2 rounded-full bg-green-500"></div>
          Local Engine Online
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 flex flex-col h-full min-w-0">
        {/* Header */}
        <header className="h-16 flex items-center justify-between px-4 border-b border-border bg-background/50 backdrop-blur-sm">
          <div className="flex items-center gap-4">
            <Button 
              variant="ghost" 
              size="icon" 
              onClick={() => setSidebarOpen(!isSidebarOpen)}
              className="text-muted-foreground hover:text-foreground"
            >
              <PanelLeft className="w-5 h-5" />
            </Button>
            <div className="font-medium text-foreground">TulparAI Sports Assistant</div>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="ghost" size="icon" title="View Sources" className="text-muted-foreground hover:text-foreground">
              <BookOpen className="w-5 h-5" />
            </Button>
            <Button variant="ghost" size="icon" title="Clear Chat" className="text-muted-foreground hover:text-destructive">
              <Trash2 className="w-5 h-5" />
            </Button>
          </div>
        </header>

        {/* Chat Area */}
        <div className="flex-1 overflow-y-auto p-4 md:p-8 flex flex-col">
          {/* Welcome Screen */}
          <div className="flex-1 flex flex-col items-center justify-center max-w-3xl mx-auto w-full">
            <div className="w-16 h-16 bg-primary/20 rounded-full flex items-center justify-center mb-6 border border-primary/30">
              <Zap className="w-8 h-8 text-primary" />
            </div>
            <h2 className="text-3xl font-bold text-foreground mb-3 text-center">
              Welcome to <span className="text-primary">TulparAI</span>
            </h2>
            <p className="text-muted-foreground text-center mb-10 max-w-lg">
              Your private, local-first sports science and performance advisor. Ask me anything about training, nutrition, or recovery.
            </p>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 w-full">
              {[
                { icon: Thermometer, text: "What should I eat 3 hours before a football match?" },
                { icon: Pill, text: "Is creatine safe for a 16-year-old wrestler?" },
                { icon: Moon, text: "How can I optimize sleep for muscle recovery?" },
                { icon: Flame, text: "Create a carb-loading protocol for my marathon." }
              ].map((item, i) => (
                <div 
                  key={i} 
                  onClick={() => setQuery(item.text)}
                  className="p-4 rounded-xl border border-border bg-card/50 hover:bg-card hover:border-primary/50 cursor-pointer transition-all flex items-start gap-3 group"
                >
                  <item.icon className="w-5 h-5 text-muted-foreground group-hover:text-primary mt-0.5 shrink-0" />
                  <p className="text-sm text-foreground">{item.text}</p>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Input Area */}
        <div className="p-4 md:p-6 w-full max-w-4xl mx-auto">
          {/* Agent Orchestration Preview */}
          <div className="flex items-center gap-2 mb-3 px-2 overflow-x-auto pb-1">
            <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-card border border-border text-[11px] text-muted-foreground whitespace-nowrap">
              <Search className="w-3 h-3" /> Analyzer
            </div>
            <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-card border border-border text-[11px] text-muted-foreground whitespace-nowrap">
              <Database className="w-3 h-3" /> Retriever
            </div>
            <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-card border border-border text-[11px] text-muted-foreground whitespace-nowrap">
              <Brain className="w-3 h-3" /> Reasoner
            </div>
            <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-card border border-border text-[11px] text-muted-foreground whitespace-nowrap">
              <ShieldCheck className="w-3 h-3" /> Verifier
            </div>
          </div>

          <div className="relative flex items-end gap-2 bg-card border border-border rounded-2xl p-2 shadow-sm focus-within:ring-1 focus-within:ring-primary focus-within:border-primary transition-all">
            <Button variant="ghost" size="icon" className="shrink-0 text-muted-foreground hover:text-foreground rounded-xl h-10 w-10">
              <ImageIcon className="w-5 h-5" />
            </Button>
            
            <Textarea 
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              placeholder="Ask TulparAI about your training..."
              className="min-h-[40px] max-h-[200px] border-0 focus-visible:ring-0 px-0 py-2.5 resize-none bg-transparent"
              rows={1}
            />

            <div className="flex items-center gap-1 shrink-0 pb-0.5">
              <Button variant="ghost" size="icon" className="text-muted-foreground hover:text-foreground rounded-xl h-10 w-10">
                <Mic className="w-5 h-5" />
              </Button>
              <Button 
                size="icon" 
                disabled={!message.trim()}
                className="bg-primary text-primary-foreground hover:bg-primary/90 rounded-xl h-10 w-10 disabled:opacity-50"
              >
                <Send className="w-4 h-4 ml-0.5" />
              </Button>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
