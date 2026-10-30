
import { useState } from "react";
import {
  Scale,
  MessageSquare,
  FileText,
  Mic,
  Languages,
  ShieldCheck,
  UserRound,
  ArrowRight,
} from "lucide-react";
import "./App.css";

function App() {
  const [message, setMessage] = useState("");

  const features = [
    {
      icon: MessageSquare,
      title: "AI Legal Chatbot",
      text: "Ask legal questions and get simple, easy-to-understand information.",
    },
    {
      icon: FileText,
      title: "Document Analyzer",
      text: "Upload legal documents and understand important clauses and terms.",
    },
    {
      icon: Mic,
      title: "Voice Assistance",
      text: "Interact with LexAI using voice for a more natural experience.",
    },
    {
      icon: Languages,
      title: "Multilingual Support",
      text: "Access legal information in multiple languages.",
    },
    {
      icon: ShieldCheck,
      title: "Privacy & Security",
      text: "Designed with privacy and secure handling of legal information.",
    },
    {
      icon: UserRound,
      title: "Lawyer Referral",
      text: "Connect with a qualified lawyer when professional help is needed.",
    },
  ];

  return (
    <div className="app">
      <nav className="navbar">
        <div className="logo">
          <div className="logo-icon">
            <Scale size={25} />
          </div>
          <span>
            Lex<span>AI</span>
          </span>
        </div>

        <div className="nav-links">
          <a href="#home">Home</a>
          <a href="#features">Features</a>
          <a href="#about">About</a>
        </div>

        <button className="nav-button">
          Get Started <ArrowRight size={17} />
        </button>
      </nav>

      <main>
        <section className="hero" id="home">
          <div className="hero-text">
            <div className="badge">
              <Scale size={16} />
              AI-Powered Legal Assistant
            </div>

            <h1>
              Legal clarity,
              <br />
              <span>made simple.</span>
            </h1>

            <p>
              LexAI helps you understand legal concepts and documents
              through simple, accessible AI-powered assistance.
            </p>

            <div className="hero-buttons">
              <button className="primary-btn">
                Start with LexAI <ArrowRight size={18} />
              </button>

              <button className="secondary-btn">
                Analyze a Document
              </button>
            </div>

            <p className="disclaimer">
              LexAI provides legal information, not legal advice.
            </p>
          </div>

          <div className="chat-card">
            <div className="chat-header">
              <div className="chat-profile">
                <div className="avatar">
                  <Scale size={22} />
                </div>

                <div>
                  <strong>LexAI Assistant</strong>
                  <small>Online • Ready to help</small>
                </div>
              </div>

              <span className="online-dot"></span>
            </div>

            <div className="chat-body">
              <div className="message bot-message">
                Hello! 👋 I'm LexAI.
                <br />
                How can I help you understand the law today?
              </div>

              <div className="message user-message">
                What is a legal contract?
              </div>

              <div className="message bot-message">
                A legal contract is an agreement between parties that
                creates legally enforceable obligations.
              </div>
            </div>

            <div className="chat-input">
              <input
                type="text"
                placeholder="Ask a legal question..."
                value={message}
                onChange={(e) => setMessage(e.target.value)}
              />

              <button>
                <ArrowRight size={18} />
              </button>
            </div>
          </div>
        </section>

        <section className="features-section" id="features">
          <div className="section-heading">
            <span>POWERFUL FEATURES</span>

            <h2>Everything you need to understand the law</h2>

            <p>
              One intelligent platform for accessible and simplified
              legal information.
            </p>
          </div>

          <div className="features-grid">
            {features.map((feature) => {
              const Icon = feature.icon;

              return (
                <div className="feature-card" key={feature.title}>
                  <div className="feature-icon">
                    <Icon size={24} />
                  </div>

                  <h3>{feature.title}</h3>

                  <p>{feature.text}</p>

                  <button>
                    Explore <ArrowRight size={15} />
                  </button>
                </div>
              );
            })}
          </div>
        </section>

        <section className="about-section" id="about">
          <div>
            <span>ABOUT LEXAI</span>

            <h2>
              Making legal information easier to understand.
            </h2>
          </div>

          <p>
            LexAI combines conversational AI, document analysis,
            language support and secure technology to make legal
            information more accessible to users.
          </p>
        </section>
      </main>

      <footer>
        <div className="logo">
          <div className="logo-icon">
            <Scale size={20} />
          </div>

          <span>
            Lex<span>AI</span>
          </span>
        </div>

        <p>
          © 2026 LexAI. AI-powered legal information assistant.
        </p>
      </footer>
    </div>
  );
}

export default App; 