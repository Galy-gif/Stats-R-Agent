import { useState, useRef, useEffect } from 'react'
import { sendQuestion } from '../api/chat'
import './ChatWindow.css'

function Message({ role, content }) {
  return (
    <div className={`message ${role}`}>
      <div className="bubble">
        <pre className="content">{content}</pre>
      </div>
    </div>
  )
}

export default function ChatWindow() {
  const [messages, setMessages] = useState([
    { role: 'assistant', content: '你好！我是 Stats-R-Agent，可以回答统计学原理和 R 语言相关问题。请输入你的问题 👇' },
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  async function handleSubmit(e) {
    e.preventDefault()
    const question = input.trim()
    if (!question || loading) return

    setMessages(prev => [...prev, { role: 'user', content: question }])
    setInput('')
    setLoading(true)

    try {
      const answer = await sendQuestion(question)
      setMessages(prev => [...prev, { role: 'assistant', content: answer }])
    } catch (err) {
      const detail = err.response?.data?.detail || err.message || '请求失败'
      setMessages(prev => [...prev, { role: 'assistant', content: `⚠️ 错误：${detail}` }])
    } finally {
      setLoading(false)
    }
  }

  function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      handleSubmit(e)
    }
  }

  return (
    <div className="chat-window">
      <header className="chat-header">
        <h1>Stats-R-Agent</h1>
        <span className="subtitle">统计学 · R 语言 · RAG 问答</span>
      </header>

      <div className="message-list">
        {messages.map((m, i) => (
          <Message key={i} role={m.role} content={m.content} />
        ))}
        {loading && (
          <div className="message assistant">
            <div className="bubble loading">
              <span /><span /><span />
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <form className="input-area" onSubmit={handleSubmit}>
        <textarea
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="输入问题，Enter 发送，Shift+Enter 换行..."
          rows={2}
          disabled={loading}
        />
        <button type="submit" disabled={loading || !input.trim()}>
          发送
        </button>
      </form>
    </div>
  )
}
