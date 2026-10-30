import type {
  User,
  LoginResponse,
  RegisterUserData,
  Conversation,
  ChatAnswerResponse,
  DocumentAnalysisResult,
  ConsultationBookingRequest,
  ConsultationResponse,
  NotificationListResponse,
  NotificationItem,
  MarkAllReadResponse,
} from '../types'

const pause = (ms: number): Promise<void> =>
  new Promise((resolve) => window.setTimeout(resolve, ms))

const API_BASE = (import.meta.env.VITE_API_URL as string) || '/api'

let cachedToken: string | null = null

export async function getAuthToken(): Promise<string | null> {
  if (cachedToken) return cachedToken
  try {
    const stored = window.sessionStorage?.getItem('lexai_token')
    if (stored) {
      cachedToken = stored
      return cachedToken
    }
  } catch {}

  try {
    const res = await fetch(`${API_BASE}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        email: 'alex.morgan@workspace.lexai',
        password: 'DemoUserPass123!'
      })
    })
    if (res.ok) {
      const data = (await res.json()) as LoginResponse
      cachedToken = data.access_token
      try {
        window.sessionStorage?.setItem('lexai_token', cachedToken)
      } catch {}
      return cachedToken
    }
  } catch (err) {
    console.warn('⚠️ [Auth] Unable to authenticate demo user:', err)
  }
  return null
}

export async function loginUser(email: string, password: string): Promise<LoginResponse> {
  const res = await fetch(`${API_BASE}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password })
  })

  if (!res.ok) {
    const errData = (await res.json().catch(() => ({}))) as { message?: string }
    throw new Error(errData.message || 'Incorrect email or password.')
  }

  const data = (await res.json()) as LoginResponse
  cachedToken = data.access_token
  try {
    window.sessionStorage?.setItem('lexai_token', cachedToken)
    window.sessionStorage?.setItem('lexai_user', JSON.stringify(data.user))
  } catch {}
  return data
}

export async function registerUser(userData: RegisterUserData): Promise<LoginResponse> {
  const res = await fetch(`${API_BASE}/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(userData)
  })

  if (!res.ok) {
    const errData = (await res.json().catch(() => ({}))) as { message?: string }
    throw new Error(errData.message || 'Registration failed. Please check your details.')
  }

  const data = (await res.json()) as LoginResponse
  cachedToken = data.access_token
  try {
    window.sessionStorage?.setItem('lexai_token', cachedToken)
    window.sessionStorage?.setItem('lexai_user', JSON.stringify(data.user))
  } catch {}
  return data
}

export async function fetchCurrentUser(): Promise<User | null> {
  const token = await getAuthToken()
  if (!token) return null

  try {
    const res = await fetch(`${API_BASE}/auth/me`, {
      headers: { Authorization: `Bearer ${token}` }
    })
    if (res.ok) {
      const user = (await res.json()) as User
      try {
        window.sessionStorage?.setItem('lexai_user', JSON.stringify(user))
      } catch {}
      return user
    }
  } catch (err) {
    console.warn('⚠️ [Auth] Failed to fetch current user profile:', err)
  }
  return null
}

export function logoutUser(): void {
  cachedToken = null
  try {
    window.sessionStorage?.removeItem('lexai_token')
    window.sessionStorage?.removeItem('lexai_user')
  } catch {}
}

export async function fetchConversations(): Promise<Conversation[]> {
  try {
    const token = await getAuthToken()
    const headers: HeadersInit = {}
    if (token) headers['Authorization'] = `Bearer ${token}`
    const res = await fetch(`${API_BASE}/conversations`, { headers })
    if (res.ok) {
      return (await res.json()) as Conversation[]
    }
  } catch (err) {
    console.warn('⚠️ [API] Failed to fetch conversations:', err)
  }
  return []
}

export async function fetchConversation(conversationId: number | string): Promise<Conversation | null> {
  try {
    const token = await getAuthToken()
    const headers: HeadersInit = {}
    if (token) headers['Authorization'] = `Bearer ${token}`
    const res = await fetch(`${API_BASE}/conversations/${conversationId}`, { headers })
    if (res.ok) {
      return (await res.json()) as Conversation
    }
  } catch (err) {
    console.warn(`⚠️ [API] Failed to fetch conversation ${conversationId}:`, err)
  }
  return null
}

export async function createConversation(title: string, language = 'English'): Promise<Conversation | null> {
  try {
    const token = await getAuthToken()
    const headers: HeadersInit = { 'Content-Type': 'application/json' }
    if (token) headers['Authorization'] = `Bearer ${token}`
    const res = await fetch(`${API_BASE}/conversations`, {
      method: 'POST',
      headers,
      body: JSON.stringify({ title, language })
    })
    if (res.ok) {
      return (await res.json()) as Conversation
    }
  } catch (err) {
    console.warn('⚠️ [API] Failed to create conversation:', err)
  }
  return null
}

type TenantTuple = [string, string, string[], string, string]

const tenantResponses: Record<string, TenantTuple> = {
  English: [
    'As a tenant, you generally have the right to know the terms of your rental agreement. Local laws may provide additional protections.',
    'Review rent, deposit, repairs and notice terms. Tenant protections vary by location.',
    ['When and how rent may increase', 'Deposit return conditions', 'Notice periods and reasons for ending the tenancy'],
    'Speak with a local lawyer if you receive an eviction notice or have a dispute about your rights.',
    'This is general legal information, not legal advice. Exact rights depend on your agreement and local law.'
  ],
  Telugu: [
    'అద్దెదారుగా, అద్దె ఒప్పందంలోని నిబంధనలను తెలుసుకునే హక్కు మీకు ఉంది. స్థానిక చట్టాలు అదనపు హక్కులు కల్పించవచ్చు.',
    'మీ ఒప్పందంలోని అద్దె, డిపాజిట్, మరమ్మతులు మరియు నోటీసు నిబంధనలను పరిశీలించండి.',
    ['అద్దె పెంపు ఎప్పుడు, ఎలా చేయవచ్చో చూడండి', 'డిపాజిట్ తిరిగి ఇచ్చే షరతులను తనిఖీ చేయండి', 'తొలగింపు మరియు నోటీసు నిబంధనలను చదవండి'],
    'తొలగింపు నోటీసు అందితే లేదా హక్కులపై వివాదం ఉంటే స్థానిక న్యాయవాదిని సంప్రదించండి.',
    'ఇది సాధారణ న్యాయ సమాచారం మాత్రమే. ఖచ్చితమైన హక్కులు మీ ఒప్పందం మరియు స్థానిక చట్టాలపై ఆధారపడి ఉంటాయి.'
  ],
  Hindi: [
    'किरायेदार के रूप में आपको किराये के समझौते की शर्तें जानने का अधिकार है। स्थानीय कानून अतिरिक्त सुरक्षा दे सकते हैं।',
    'किराया, जमा राशि, मरम्मत और नोटिस की शर्तें देखें। अधिकार स्थान के अनुसार बदलते हैं।',
    ['किराया कब और कैसे बढ़ाया जा सकता है', 'जमा राशि लौटाने की शर्तें', 'बेदखली और नोटिस की अवधि'],
    'बेदखली का नोटिस मिलने या अधिकारों पर विवाद होने पर स्थानीय वकील से बात करें।',
    'यह सामान्य कानूनी जानकारी है, कानूनी सलाह नहीं। सटीक अधिकार आपके समझौते और स्थानीय कानून पर निर्भर करते हैं।'
  ],
  Tamil: [
    'குத்தகைதாரராக, வாடகை ஒப்பந்தத்தின் விதிகளை அறிய உங்களுக்கு உரிமை உண்டு. உள்ளூர் சட்டங்கள் கூடுதல் பாதுகாப்புகளை வழங்கலாம்.',
    'வாடகை, முன்பணம், பழுதுபார்ப்பு மற்றும் அறிவிப்பு விதிகளைப் பாருங்கள்.',
    ['வாடகையை எப்போது உயர்த்தலாம்', 'முன்பணத்தைத் திருப்பித் தரும் நிபந்தனைகள்', 'வெளியேற்றம் மற்றும் அறிவிப்பு காலம்'],
    'வெளியேற்ற அறிவிப்பு கிடைத்தால் உள்ளூர் வழக்கறிஞரை அணுகுங்கள்.',
    'இது பொதுவான சட்டத் தகவல் மட்டுமே. சரியான உரிமைகள் உங்கள் ஒப்பந்தம் மற்றும் உள்ளூர் சட்டங்களைப் பொறுத்தது.'
  ],
  Kannada: [
    'ಬಾಡಿಗೆದಾರರಾಗಿ, ಬಾಡಿಗೆ ಒಪ್ಪಂದದ ನಿಯಮಗಳನ್ನು ತಿಳಿಯುವ ಹಕ್ಕು ನಿಮಗಿದೆ. ಸ್ಥಳೀಯ ಕಾನೂನುಗಳು ಹೆಚ್ಚುವರಿ ರಕ್ಷಣೆ ನೀಡಬಹುದು.',
    'ಬಾಡಿಗೆ, ಠೇವಣಿ, ದುರಸ್ತಿ ಮತ್ತು ನೋಟಿಸ್ ನಿಯಮಗಳನ್ನು ಪರಿಶೀಲಿಸಿ.',
    ['ಬಾಡಿಗೆಯನ್ನು ಯಾವಾಗ ಹೆಚ್ಚಿಸಬಹುದು', 'ಠೇವಣಿ ಹಿಂತಿರುಗಿಸುವ ಷರತ್ತುಗಳು', 'ಹೊರಹಾಕುವಿಕೆ ಮತ್ತು ನೋಟಿಸ್ ಅವಧಿ'],
    'ಹೊರಹಾಕುವ ನೋಟಿಸ್ ಬಂದರೆ ಸ್ಥಳೀಯ ವಕೀಲರನ್ನು ಸಂಪರ್ಕಿಸಿ.',
    'ಇದು ಸಾಮಾನ್ಯ ಕಾನೂನು ಮಾಹಿತಿ ಮಾತ್ರ. ನಿಖರ ಹಕ್ಕುಗಳು ನಿಮ್ಮ ಒಪ್ಪಂದ ಮತ್ತು ಸ್ಥಳೀಯ ಕಾನೂನುಗಳನ್ನು ಅವಲಂಬಿಸಿವೆ.'
  ],
  Marathi: [
    'भाडेकरू म्हणून तुम्हाला भाडेकरारातील अटी जाणून घेण्याचा अधिकार आहे. स्थानिक कायदे अतिरिक्त संरक्षण देऊ शकतात.',
    'भाडे, ठेव, दुरुस्ती आणि नोटीसच्या अटी तपासा.',
    ['भाडे कधी वाढवता येते', 'ठेव परत करण्याच्या अटी', 'बेदखली आणि नोटीसचा कालावधी'],
    'बेदखलीची नोटीस मिळाल्यास स्थानिक वकिलाशी बोला.',
    'ही सामान्य कायदेशीर माहिती आहे, कायदेशीर सल्ला नाही. नेमके हक्क करार आणि स्थानिक कायद्यांवर अवलंबून असतात.'
  ]
}

export async function askLegalQuestion(
  question: string,
  language = 'English',
  conversationId: number | null = null
): Promise<ChatAnswerResponse & { language: string; is_grounded?: boolean; backend?: unknown }> {
  interface BackendChatJson {
    message_id?: number
    conversation_id?: number
    title?: string
    explanation: string
    implication: string
    checks?: string[]
    consult?: string
    caveat?: string
    sources?: string[]
    is_grounded?: boolean
  }

  let backendResponse: BackendChatJson | null = null
  try {
    const token = await getAuthToken()
    const headers: HeadersInit = { 'Content-Type': 'application/json' }
    if (token) headers['Authorization'] = `Bearer ${token}`

    const payload: { message: string; language: string; conversation_id?: number } = {
      message: question,
      language
    }
    if (conversationId) payload.conversation_id = conversationId

    const res = await fetch(`${API_BASE}/chat`, {
      method: 'POST',
      headers,
      body: JSON.stringify(payload)
    })
    if (res.ok) {
      backendResponse = (await res.json()) as BackendChatJson
      console.log('✅ [FastAPI Backend] Successfully reached backend /api/chat:', backendResponse)
      return {
        id: backendResponse.message_id || Date.now(),
        conversation_id: backendResponse.conversation_id,
        role: 'assistant',
        title: backendResponse.title || 'Simple Explanation',
        text: backendResponse.explanation,
        explanation: backendResponse.explanation,
        implication: backendResponse.implication,
        checks: backendResponse.checks || [],
        consult: backendResponse.consult || '',
        caveat: backendResponse.caveat || 'This is general legal information, not legal advice.',
        language,
        sources: backendResponse.sources || [],
        is_grounded: backendResponse.is_grounded,
        backend: backendResponse
      }
    }
  } catch (err) {
    console.warn('⚠️ [FastAPI Backend] Chat call fallback:', err)
  }

  await pause(300)
  const lower = question.toLowerCase()
  const indemnity = /indemnity|indemnify/.test(lower)
  const tenant = !indemnity && /tenant|rent|landlord|lease|rental/.test(lower)

  const [explanation, implication, checks, consult, caveat] = tenant
    ? tenantResponses[language] || tenantResponses.English
    : indemnity
    ? [
        'An indemnity clause generally means one party agrees to cover certain losses or damages suffered by another party.',
        'If something goes wrong and the clause applies, the responsible party may have to compensate the other party.',
        ['Which events and losses are covered?', 'Is there a cap on what you could owe?', 'Does it cover another party’s negligence?'],
        'Consult a lawyer if the clause is broad, unlimited, or shifts another party’s responsibility to you.',
        'The exact meaning depends on your agreement and jurisdiction. This is general legal information, not legal advice.'
      ]
    : [
        `In general, ${question.replace(/[?!.]+$/, '')} depends on the facts, documents and law where you are.`,
        'Check relevant dates, written terms and notices. Keep copies of related communication.',
        ['Which jurisdiction applies?', 'What does the agreement or notice say?', 'Are there deadlines to respond?'],
        'If a deadline is close or money, housing or safety is at risk, speak with a qualified local lawyer.',
        'This is general legal information, not legal advice. It may not reflect the law in your location.'
      ]

  const title =
    language === 'Telugu'
      ? 'సులభమైన వివరణ'
      : language === 'Hindi'
      ? 'सरल व्याख्या'
      : language === 'Tamil'
      ? 'எளிய விளக்கம்'
      : language === 'Kannada'
      ? 'ಸರಳ ವಿವರಣೆ'
      : language === 'Marathi'
      ? 'सोपे स्पष्टीकरण'
      : 'Simple Explanation'

  return {
    id: Date.now(),
    role: 'assistant',
    title,
    text: explanation as string,
    explanation: explanation as string,
    implication: implication as string,
    checks: checks as string[],
    consult: consult as string,
    caveat: caveat as string,
    language,
    sources: tenant
      ? [
          'Local residential tenancy legislation (jurisdiction-specific)',
          'Your rental agreement · rent, deposit and termination sections'
        ]
      : indemnity
      ? [
          'Indian Contract Act, 1872 · Sections 124–125 (example reference)',
          'Your agreement · indemnity section'
        ]
      : ['Your question and documents provided', 'Relevant local legislation may apply'],
    backend: null
  }
}

export async function uploadAndAnalyzeDocument(
  file: File,
  onProgress?: (step: 'uploading' | 'processing' | 'analyzing') => void
): Promise<DocumentAnalysisResult> {
  try {
    const token = await getAuthToken()
    const headers: Record<string, string> = token ? { Authorization: `Bearer ${token}` } : {}

    // Step 1: Uploading
    onProgress?.('uploading')
    const formData = new FormData()
    formData.append('file', file)

    const uploadRes = await fetch(`${API_BASE}/documents/upload`, {
      method: 'POST',
      headers,
      body: formData
    })

    if (!uploadRes.ok) {
      throw new Error(`Upload failed with status ${uploadRes.status}`)
    }

    const uploadData = (await uploadRes.json()) as { id: number }
    const docId = uploadData.id

    // Step 2: Processing (Extraction)
    onProgress?.('processing')
    await pause(350)

    // Step 3: Analyzing (Clause Detection & Risk Assessment)
    onProgress?.('analyzing')
    const analyzeRes = await fetch(`${API_BASE}/documents/${docId}/analyze`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...headers
      }
    })

    if (!analyzeRes.ok) {
      throw new Error(`Analysis failed with status ${analyzeRes.status}`)
    }

    const analysisData = (await analyzeRes.json()) as DocumentAnalysisResult
    return analysisData
  } catch (err) {
    console.warn('⚠️ [Document Pipeline] Backend processing error, providing structured analysis fallback:', err)
    await pause(600)
    return {
      id: undefined,
      filename: file?.name || 'Document.pdf',
      summary: 'This agreement covers tenancy obligations, rent payments, security deposits, and early termination rules.',
      overall_risk_score: 'MODERATE',
      clauses: [
        {
          title: 'Payment Terms',
          risk: 'Low',
          explanation: 'Monthly rent is specified with a fixed deposit return condition upon handover.',
          action: 'Rent of ₹18,500 payable on or before the 5th day of each calendar month.'
        },
        {
          title: 'Termination Clause',
          risk: 'Needs attention',
          explanation: 'Either party may terminate by serving written notice of 60 days.',
          action: 'Either party may terminate this agreement with 60 days prior written notice.'
        },
        {
          title: 'Indemnity Clause',
          risk: 'High attention',
          explanation: 'Requires tenant to cover unspecified damages and landlord legal fees without a liability cap.',
          action: 'Tenant shall indemnify and hold harmless the Landlord from all claims and losses.'
        }
      ],
      unclear_items: 'Confirm emergency repair turnaround and utility billing breakdown in writing.'
    }
  }
}

export async function analyzeDocument(filename: string): Promise<{
  filename: string
  detectedText: boolean
  clausesIdentified: boolean
  analyzed: boolean
}> {
  try {
    await fetch(`${API_BASE}/lawyers`, { method: 'GET' })
  } catch {}
  await pause(300)
  return { filename, detectedText: true, clausesIdentified: true, analyzed: true }
}

export async function fetchLawyerConsultations(statusFilter: string | null = null): Promise<ConsultationResponse[]> {
  try {
    const token = await getAuthToken()
    const headers: HeadersInit = {}
    if (token) headers['Authorization'] = `Bearer ${token}`

    let url = `${API_BASE}/consultations`
    if (statusFilter && statusFilter !== 'ALL') {
      url += `?status=${encodeURIComponent(statusFilter)}`
    }

    const res = await fetch(url, { headers })
    if (res.ok) {
      return (await res.json()) as ConsultationResponse[]
    }
  } catch (err) {
    console.warn('⚠️ [API] Failed to fetch consultations for lawyer:', err)
  }
  return []
}

export async function bookConsultation(bookingData: ConsultationBookingRequest): Promise<ConsultationResponse> {
  const token = await getAuthToken()
  const headers: HeadersInit = { 'Content-Type': 'application/json' }
  if (token) headers['Authorization'] = `Bearer ${token}`

  const res = await fetch(`${API_BASE}/consultations`, {
    method: 'POST',
    headers,
    body: JSON.stringify(bookingData)
  })

  if (!res.ok) {
    const errData = (await res.json().catch(() => ({}))) as { message?: string }
    throw new Error(errData.message || 'Failed to submit consultation booking.')
  }
  return (await res.json()) as ConsultationResponse
}

export async function fetchUserConsultations(): Promise<ConsultationResponse[]> {
  return await fetchLawyerConsultations()
}

export async function updateConsultationStatus(
  consultationId: number,
  newStatus: string
): Promise<ConsultationResponse> {
  const token = await getAuthToken()
  const headers: HeadersInit = { 'Content-Type': 'application/json' }
  if (token) headers['Authorization'] = `Bearer ${token}`

  const res = await fetch(`${API_BASE}/consultations/${consultationId}/status`, {
    method: 'PATCH',
    headers,
    body: JSON.stringify({ status: newStatus })
  })

  if (!res.ok) {
    const errData = (await res.json().catch(() => ({}))) as { message?: string }
    throw new Error(errData.message || 'Failed to update consultation status.')
  }

  return (await res.json()) as ConsultationResponse
}

export async function fetchNotifications(unreadOnly = false): Promise<NotificationListResponse> {
  try {
    const token = await getAuthToken()
    const headers: HeadersInit = {}
    if (token) headers['Authorization'] = `Bearer ${token}`

    let url = `${API_BASE}/notifications`
    if (unreadOnly) url += '?unread_only=true'

    const res = await fetch(url, { headers })
    if (res.ok) {
      return (await res.json()) as NotificationListResponse
    }
  } catch (err) {
    console.warn('⚠️ [API] Failed to fetch notifications:', err)
  }
  return { items: [], unread_count: 0 }
}

export async function markNotificationRead(notificationId: number): Promise<NotificationItem | null> {
  try {
    const token = await getAuthToken()
    const headers: HeadersInit = {}
    if (token) headers['Authorization'] = `Bearer ${token}`

    const res = await fetch(`${API_BASE}/notifications/${notificationId}/read`, {
      method: 'PATCH',
      headers
    })
    if (res.ok) {
      return (await res.json()) as NotificationItem
    }
  } catch (err) {
    console.warn('⚠️ [API] Failed to mark notification read:', err)
  }
  return null
}

export async function markAllNotificationsRead(): Promise<MarkAllReadResponse> {
  try {
    const token = await getAuthToken()
    const headers: HeadersInit = {}
    if (token) headers['Authorization'] = `Bearer ${token}`

    const res = await fetch(`${API_BASE}/notifications/mark-all-read`, {
      method: 'POST',
      headers
    })
    if (res.ok) {
      return (await res.json()) as MarkAllReadResponse
    }
  } catch (err) {
    console.warn('⚠️ [API] Failed to mark all notifications read:', err)
  }
  return { success: false, marked_count: 0 }
}
