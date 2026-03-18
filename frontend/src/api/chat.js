import axios from 'axios'

export async function sendQuestion(question, history = []) {
  const res = await axios.post('/api/chat', { question, history })
  return res.data.answer
}
