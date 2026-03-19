import { useState, useRef, useEffect } from 'react'
import { sendQuestion, sendFeedback } from '../api/chat'
import './ChatWindow.css'

function FeedbackButtons({ query, content, messageId, ratings, onRate }) {
  const current = ratings[messageId]

  async function handleRate(value) {
    if (current === value) return   // 已评过，不重复
    onRate(messageId, value)
    try {
      await sendFeedback(query, content, value)
    } catch {
      // 静默失败，不影响用户体验
    }
  }

  return (
    <div className="feedback-buttons">
      <button
        className={`feedback-btn${current === 1 ? ' active-up' : ''}`}
        onClick={() => handleRate(1)}
        title="有用"
        aria-label="有用"
      >👍</button>
      <button
        className={`feedback-btn${current === -1 ? ' active-down' : ''}`}
        onClick={() => handleRate(-1)}
        title="无用"
        aria-label="无用"
      >👎</button>
    </div>
  )
}

function Message({ msg, ratings, onRate }) {
  const { role, content, id, query } = msg
  return (
    <div className={`message ${role}`}>
      <div className="bubble">
        <pre className="content">{content}</pre>
        {role === 'assistant' && query && (
          <FeedbackButtons
            query={query}
            content={content}
            messageId={id}
            ratings={ratings}
            onRate={onRate}
          />
        )}
      </div>
    </div>
  )
}

const WELCOME = '你好！我是 Stats-R-Agent，一位严谨的统计学与 R 语言助教。\n\n' +
  '当你提出统计分析需求时，我会先确认数据是否满足前提假设条件，再为你生成完整的 R 代码。\n\n' +
  '请输入你的问题 👇'

let _id = 0
const nextId = () => ++_id

export default function ChatWindow() {
  const [messages, setMessages] = useState([
    { id: nextId(), role: 'assistant', content: WELCOME, query: null },
  ])
  const [history, setHistory] = useState([])
  const [ratings, setRatings] = useState({})   // { messageId: 1 | -1 }
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  function handleRate(messageId, value) {
    setRatings(prev => ({ ...prev, [messageId]: value }))
  }

  async function handleSubmit(e) {
    e.preventDefault()
    const question = input.trim()
    if (!question || loading) return

    const userMsg = { id: nextId(), role: 'user', content: question, query: null }
    setMessages(prev => [...prev, userMsg])
    setInput('')
    setLoading(true)

    try {
      const answer = await sendQuestion(question, history)
      const assistantMsg = { id: nextId(), role: 'assistant', content: answer, query: question }
      setMessages(prev => [...prev, assistantMsg])
      setHistory(prev => [
        ...prev,
        { role: 'user', content: question },
        { role: 'assistant', content: answer },
      ])
    } catch (err) {
      const detail = err.response?.data?.detail || err.message || '请求失败'
      setMessages(prev => [...prev, {
        id: nextId(), role: 'assistant', content: `⚠️ 错误：${detail}`, query: null,
      }])
    } finally {
      setLoading(false)
    }
  }

  function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) handleSubmit(e)
  }

  return (
    <div className="chat-window">
      <header className="chat-header">
        <h1>Stats-R-Agent</h1>
        <span className="subtitle">统计学 · R 语言 · 护栏问答</span>
      </header>

      <div className="message-list">
        {messages.map(m => (
          <Message key={m.id} msg={m} ratings={ratings} onRate={handleRate} />
        ))}
        {loading && (
          <div className="message assistant">
            <div className="bubble loading"><span /><span /><span /></div>
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
        <button type="submit" disabled={loading || !input.trim()}>发送</button>
      </form>
    </div>
  )
}
