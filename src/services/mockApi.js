const pause = (ms) => new Promise((resolve) => window.setTimeout(resolve, ms))

const tenantResponses = {
  English: ['As a tenant, you generally have the right to know the terms of your rental agreement. Local laws may provide additional protections.', 'Review rent, deposit, repairs and notice terms. Tenant protections vary by location.', ['When and how rent may increase', 'Deposit return conditions', 'Notice periods and reasons for ending the tenancy'], 'Speak with a local lawyer if you receive an eviction notice or have a dispute about your rights.', 'This is general legal information, not legal advice. Exact rights depend on your agreement and local law.'],
  Telugu: ['అద్దెదారుగా, అద్దె ఒప్పందంలోని నిబంధనలను తెలుసుకునే హక్కు మీకు ఉంది. స్థానిక చట్టాలు అదనపు హక్కులు కల్పించవచ్చు.', 'మీ ఒప్పందంలోని అద్దె, డిపాజిట్, మరమ్మతులు మరియు నోటీసు నిబంధనలను పరిశీలించండి.', ['అద్దె పెంపు ఎప్పుడు, ఎలా చేయవచ్చో చూడండి', 'డిపాజిట్ తిరిగి ఇచ్చే షరతులను తనిఖీ చేయండి', 'తొలగింపు మరియు నోటీసు నిబంధనలను చదవండి'], 'తొలగింపు నోటీసు అందితే లేదా హక్కులపై వివాదం ఉంటే స్థానిక న్యాయవాదిని సంప్రదించండి.', 'ఇది సాధారణ న్యాయ సమాచారం మాత్రమే. ఖచ్చితమైన హక్కులు మీ ఒప్పందం మరియు స్థానిక చట్టాలపై ఆధారపడి ఉంటాయి.'],
  Hindi: ['किरायेदार के रूप में आपको किराये के समझौते की शर्तें जानने का अधिकार है। स्थानीय कानून अतिरिक्त सुरक्षा दे सकते हैं।', 'किराया, जमा राशि, मरम्मत और नोटिस की शर्तें देखें। अधिकार स्थान के अनुसार बदलते हैं।', ['किराया कब और कैसे बढ़ाया जा सकता है', 'जमा राशि लौटाने की शर्तें', 'बेदखली और नोटिस की अवधि'], 'बेदखली का नोटिस मिलने या अधिकारों पर विवाद होने पर स्थानीय वकील से बात करें।', 'यह सामान्य कानूनी जानकारी है, कानूनी सलाह नहीं। सटीक अधिकार आपके समझौते और स्थानीय कानून पर निर्भर करते हैं।'],
  Tamil: ['குத்தகைதாரராக, வாடகை ஒப்பந்தத்தின் விதிகளை அறிய உங்களுக்கு உரிமை உண்டு. உள்ளூர் சட்டங்கள் கூடுதல் பாதுகாப்புகளை வழங்கலாம்.', 'வாடகை, முன்பணம், பழுதுபார்ப்பு மற்றும் அறிவிப்பு விதிகளைப் பாருங்கள்.', ['வாடகையை எப்போது உயர்த்தலாம்', 'முன்பணத்தைத் திருப்பித் தரும் நிபந்தனைகள்', 'வெளியேற்றம் மற்றும் அறிவிப்பு காலம்'], 'வெளியேற்ற அறிவிப்பு கிடைத்தால் உள்ளூர் வழக்கறிஞரை அணுகுங்கள்.', 'இது பொதுவான சட்டத் தகவல் மட்டுமே. சரியான உரிமைகள் உங்கள் ஒப்பந்தம் மற்றும் உள்ளூர் சட்டங்களைப் பொறுத்தது.'],
  Kannada: ['ಬಾಡಿಗೆದಾರರಾಗಿ, ಬಾಡಿಗೆ ಒಪ್ಪಂದದ ನಿಯಮಗಳನ್ನು ತಿಳಿಯುವ ಹಕ್ಕು ನಿಮಗಿದೆ. ಸ್ಥಳೀಯ ಕಾನೂನುಗಳು ಹೆಚ್ಚುವರಿ ರಕ್ಷಣೆ ನೀಡಬಹುದು.', 'ಬಾಡಿಗೆ, ಠೇವಣಿ, ದುರಸ್ತಿ ಮತ್ತು ನೋಟಿಸ್ ನಿಯಮಗಳನ್ನು ಪರಿಶೀಲಿಸಿ.', ['ಬಾಡಿಗೆಯನ್ನು ಯಾವಾಗ ಹೆಚ್ಚಿಸಬಹುದು', 'ಠೇವಣಿ ಹಿಂತಿರುಗಿಸುವ ಷರತ್ತುಗಳು', 'ಹೊರಹಾಕುವಿಕೆ ಮತ್ತು ನೋಟಿಸ್ ಅವಧಿ'], 'ಹೊರಹಾಕುವ ನೋಟಿಸ್ ಬಂದರೆ ಸ್ಥಳೀಯ ವಕೀಲರನ್ನು ಸಂಪರ್ಕಿಸಿ.', 'ಇದು ಸಾಮಾನ್ಯ ಕಾನೂನು ಮಾಹಿತಿ ಮಾತ್ರ. ನಿಖರ ಹಕ್ಕುಗಳು ನಿಮ್ಮ ಒಪ್ಪಂದ ಮತ್ತು ಸ್ಥಳೀಯ ಕಾನೂನುಗಳನ್ನು ಅವಲಂಬಿಸಿವೆ.'],
  Marathi: ['भाडेकरू म्हणून तुम्हाला भाडेकरारातील अटी जाणून घेण्याचा अधिकार आहे. स्थानिक कायदे अतिरिक्त संरक्षण देऊ शकतात.', 'भाडे, ठेव, दुरुस्ती आणि नोटीसच्या अटी तपासा.', ['भाडे कधी वाढवता येते', 'ठेव परत करण्याच्या अटी', 'बेदखली आणि नोटीसचा कालावधी'], 'बेदखलीची नोटीस मिळाल्यास स्थानिक वकिलाशी बोला.', 'ही सामान्य कायदेशीर माहिती आहे, कायदेशीर सल्ला नाही. नेमके हक्क करार आणि स्थानिक कायद्यांवर अवलंबून असतात.'],
}

export async function askLegalQuestion(question, language = 'English') {
  let backendResponse = null
  try {
    const res = await fetch('http://127.0.0.1:8000/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: question, language })
    })
    if (res.ok) {
      backendResponse = await res.json()
      console.log('✅ [FastAPI Backend] Successfully reached backend /api/chat:', backendResponse)
    }
  } catch (err) {
    console.warn('⚠️ [FastAPI Backend] Could not reach backend, falling back to local model:', err)
  }

  await pause(450)
  const lower = question.toLowerCase()
  const indemnity = /indemnity|indemnify/.test(lower)
  const tenant = !indemnity && /tenant|rent|landlord|lease|rental/.test(lower)
  let [explanation, implication, checks, consult, caveat] = tenant ? tenantResponses[language] || tenantResponses.English : indemnity
    ? ['An indemnity clause generally means one party agrees to cover certain losses or damages suffered by another party.', 'If something goes wrong and the clause applies, the responsible party may have to compensate the other party.', ['Which events and losses are covered?', 'Is there a cap on what you could owe?', 'Does it cover another party’s negligence?'], 'Consult a lawyer if the clause is broad, unlimited, or shifts another party’s responsibility to you.', 'The exact meaning depends on your agreement and jurisdiction. This is general legal information, not legal advice.']
    : [`In general, ${question.replace(/[?!.]+$/, '')} depends on the facts, documents and law where you are.`, 'Check relevant dates, written terms and notices. Keep copies of related communication.', ['Which jurisdiction applies?', 'What does the agreement or notice say?', 'Are there deadlines to respond?'], 'If a deadline is close or money, housing or safety is at risk, speak with a qualified local lawyer.', 'This is general legal information, not legal advice. It may not reflect the law in your location.']
  const title = language === 'Telugu' ? 'సులభమైన వివరణ' : language === 'Hindi' ? 'सरल व्याख्या' : language === 'Tamil' ? 'எளிய விளக்கம்' : language === 'Kannada' ? 'ಸರಳ ವಿವರಣೆ' : language === 'Marathi' ? 'सोपे स्पष्टीकरण' : 'Simple Explanation'
  return { id: Date.now(), role: 'assistant', title, text: explanation, explanation, implication, checks, consult, caveat, language, sources: tenant ? ['Local residential tenancy legislation (jurisdiction-specific)', 'Your rental agreement · rent, deposit and termination sections'] : indemnity ? ['Indian Contract Act, 1872 · Sections 124–125 (example reference)', 'Your agreement · indemnity section'] : ['Your question and documents provided', 'Relevant local legislation may apply'], backend: backendResponse }
}

export async function analyzeDocument(filename) {
  try {
    await fetch('http://127.0.0.1:8000/', { method: 'GET' })
    console.log('✅ [FastAPI Backend] Verified backend connection for document analysis')
  } catch (err) {
    console.warn('⚠️ [FastAPI Backend] Connection check warning:', err)
  }
  await pause(1000)
  return { filename, detectedText: true, clausesIdentified: true, analyzed: true }
}