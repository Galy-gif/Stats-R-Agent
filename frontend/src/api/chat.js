import axios from 'axios'

export async function sendQuestion(question, history = []) {
  const res = await axios.post('/api/chat', { question, history })
  return res.data.answer
}

export async function sendFeedback(user_query, agent_response, rating) {
  await axios.post('/api/feedback', { user_query, agent_response, rating })
}
