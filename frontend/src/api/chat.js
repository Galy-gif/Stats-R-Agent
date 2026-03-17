import axios from 'axios'

export async function sendQuestion(question) {
  const res = await axios.post('/api/chat', { question })
  return res.data.answer
}
