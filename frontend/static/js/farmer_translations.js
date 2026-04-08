/**
 * Farmer Dashboard Translations
 * Supported Languages: English (en), Hindi (hi), Telugu (te), Tamil (ta), Kannada (kn)
 */

// Initialize current language - default to English but allow switching
let _currentLang = localStorage.getItem('farmer_lang') || 'en';

// Function to update language (called when user switches language)
function updateCurrentLang(lang) {
  _currentLang = lang;
  localStorage.setItem('farmer_lang', lang);
}

const FarmerTranslations = {
  // Header & Navigation
  welcome: {
    en: "Welcome, Farmer",
    hi: "स्वागत है, किसान",
    te: "స్వాగతం, రైతు",
    ta: "வரவேற்கிறோம், விவசாயி",
    kn: "ಸ್ವಾಗತ, ರೈತ"
  },
  dashboard: {
    en: "Farmer Dashboard",
    hi: "किसान डैशबोर्ड",
    te: "రైతు డాష్‌బోర్డ్",
    ta: "விவசாயி டாஷ்போர்டு",
    kn: "ರೈತ ಡ್ಯಾಶ್‌ಬೋರ್ಡ್"
  },
  storedBatches: {
    en: "Stored Batches",
    hi: "संग्रहीत बैच",
    te: "నిల్వ ఉన్న బ్యాచ్‌లు",
    ta: "சேமித்த தொகுதிகள்",
    kn: "ಸಂಗ್ರಹಿಸಿದ ಬ್ಯಾಚ್‌ಗಳು"
  },
  logout: {
    en: "Logout",
    hi: "लॉगआउट",
    te: "లాగౌట్",
    ta: "வெளியேறு",
    kn: "ಲಾಗ್ ಔಟ್"
  },
  backToDashboard: {
    en: "Back to Dashboard",
    hi: "डैशबोर्ड पर वापस",
    te: "డాష్‌బోర్డ్‌కు తిరిగి వెళ్ళండి",
    ta: "டாஷ்போர்டுக்கு திரும்பு",
    kn: "ಡ್ಯಾಶ್‌ಬೋರ್ಡ್‌ಗೆ ಹಿಂದಿರುಗಿ"
  },

  // Submit Batch Section
  submitBatch: {
    en: "Submit Batch",
    hi: "बैच जमा करें",
    te: "బ్యాచ్ సమర్పించండి",
    ta: "தொகுதியை சமர்ப்பிக்கவும்",
    kn: "ಬ್ಯಾಚ್ ಸಲ್ಲಿಸಿ"
  },
  addCropDetails: {
    en: "Add your crop details to the supply chain",
    hi: "आपूर्ति श्रृंखला में अपनी फसल का विवरण जोड़ें",
    te: "సరఫరా గొలుసుకు మీ పంట వివరాలను చేర్చండి",
    ta: "விநியோக சங்கிலியில் உங்கள் பயிர் விவரங்களைச் சேர்க்கவும்",
    kn: "ಪೂರೈಕೆ ಸರಪಳಿಗೆ ನಿಮ್ಮ ಬೆಳೆಯ ವಿವರಗಳನ್ನು ಸೇರಿಸಿ"
  },
  selectCropName: {
    en: "Select Crop Name",
    hi: "फसल का नाम चुनें",
    te: "పంట పేరు ఎంచుకోండి",
    ta: "பயிர் பெயரைத் தேர்ந்தெடுக்கவும்",
    kn: "ಬೆಳೆಯ ಹೆಸರನ್ನು ಆಯ್ಕೆಮಾಡಿ"
  },
  selectCrop: {
    en: "Select Crop",
    hi: "फसल चुनें",
    te: "పంట ఎంచుకోండి",
    ta: "பயிரைத் தேர்ந்தெடுக்கவும்",
    kn: "ಬೆಳೆಯನ್ನು ಆಯ್ಕೆಮಾಡಿ"
  },
  quantity: {
    en: "Quantity",
    hi: "मात्रा",
    te: "పరిమాణం",
    ta: "அளவு",
    kn: "ಪ್ರಮಾಣ"
  },
  enterQuantity: {
    en: "Enter quantity",
    hi: "मात्रा दर्ज करें",
    te: "పరిమాణం నమోదు చేయండి",
    ta: "அளவை உள்ளிடவும்",
    kn: "ಪ್ರಮಾಣವನ್ನು ನಮೂದಿಸಿ"
  },
  harvestDate: {
    en: "Harvest Date",
    hi: "कटाई की तारीख",
    te: "కోత తేదీ",
    ta: "அறுவடை தேதி",
    kn: "ಕೊಯ್ಲು ದಿನಾಂಕ"
  },
  selectCity: {
    en: "Select City",
    hi: "शहर चुनें",
    te: "నగరాన్ని ఎంచుకోండి",
    ta: "நகரத்தைத் தேர்ந்தெடுக்கவும்",
    kn: "ನಗರವನ್ನು ಆಯ್ಕೆಮಾಡಿ"
  },
  openInMaps: {
    en: "Open in Maps",
    hi: "मानचित्र में खोलें",
    te: "మ్యాప్‌లో తెరవండి",
    ta: "வரைபடத்தில் திறக்கவும்",
    kn: "ಮ್ಯಾಪ್‌ನಲ್ಲಿ ತೆರೆಯಿರಿ"
  },
  selectWarehouse: {
    en: "Select Warehouse",
    hi: "गोदाम चुनें",
    te: "గోదామును ఎంచుకోండి",
    ta: "கிடங்கைத் தேர்ந்தெடுக்கவும்",
    kn: "ಗೋದಾಮನ್ನು ಆಯ್ಕೆಮಾಡಿ"
  },
  submit: {
    en: "Submit Batch",
    hi: "बैच जमा करें",
    te: "బ్యాచ్ సమర్పించండి",
    ta: "தொகுதியை சமர்ப்பிக்கவும்",
    kn: "ಬ್ಯಾಚ್ ಸಲ್ಲಿಸಿ"
  },

  // Table Headers
  batchId: {
    en: "Batch ID",
    hi: "बैच आईडी",
    te: "బ్యాచ్ ఐడి",
    ta: "தொகுதி ஐடி",
    kn: "ಬ್ಯಾಚ್ ಐಡಿ"
  },
  crop: {
    en: "Crop",
    hi: "फसल",
    te: "పంట",
    ta: "பயிர்",
    kn: "ಬೆಳೆ"
  },
  harvestDateCol: {
    en: "Harvest Date",
    hi: "कटाई की तारीख",
    te: "కోత తేదీ",
    ta: "அறுவடை தேதி",
    kn: "ಕೊಯ್ಲು ದಿನಾಂಕ"
  },
  daysSinceHarvest: {
    en: "Days Since Harvest",
    hi: "कटाई के बाद दिन",
    te: "కోత తర్వాత రోజులు",
    ta: "அறுவடைக்குப் பிறகு நாட்கள்",
    kn: "ಕೊಯ್ಲಿನ ನಂತರ ದಿನಗಳು"
  },
  freshness: {
    en: "Freshness",
    hi: "ताजगी",
    te: "తాజాదనం",
    ta: "புதுமை",
    kn: "ತಾಜಾತನ"
  },
  freshnessScore: {
    en: "Freshness (0-1)",
    hi: "ताजगी (0-1)",
    te: "తాజాదనం (0-1)",
    ta: "புதுமை (0-1)",
    kn: "ತಾಜಾತನ (0-1)"
  },
  riskStatus: {
    en: "Risk Status",
    hi: "जोखिम स्थिति",
    te: "అపాయ స్థితి",
    ta: "ஆபத்து நிலை",
    kn: "ಅಪಾಯದ ಸ್ಥಿತಿ"
  },
  farmerRiskStatus: {
    en: "Farmer Risk Status",
    hi: "किसान जोखिम स्थिति",
    te: "రైతు అపాయ స్థితి",
    ta: "விவசாயி ஆபத்து நிலை",
    kn: "ರೈತರ ಅಪಾಯದ ಸ್ಥಿತಿ"
  },
  alerts: {
    en: "Alerts",
    hi: "अलर्ट",
    te: "హెచ్చరికలు",
    ta: "எச்சரிக்கைகள்",
    kn: "ಎಚ್ಚರಿಕೆಗಳು"
  },
  warehouse: {
    en: "Warehouse",
    hi: "गोदाम",
    te: "గోదాము",
    ta: "கிடங்கு",
    kn: "ಗೋದಾಮು"
  },
  location: {
    en: "Location",
    hi: "स्थान",
    te: "స్థానం",
    ta: "இடம்",
    kn: "ಸ್ಥಳ"
  },
  status: {
    en: "Status",
    hi: "स्थिति",
    te: "స్థితి",
    ta: "நிலை",
    kn: "ಸ್ಥಿತಿ"
  },
  cropType: {
    en: "Crop Type",
    hi: "फसल का प्रकार",
    te: "పంట రకం",
    ta: "பயிர் வகை",
    kn: "ಬೆಳೆಯ ಪ್ರಕಾರ"
  },
  shelfLifeDays: {
    en: "Shelf Life Days",
    hi: "शेल्फ लाइफ दिन",
    te: "షెల్ఫ్ లైఫ్ రోజులు",
    ta: "கிடங்கு வாழ்நாள் நாட்கள்",
    kn: "ಶೆಲ್ಫ್ ಲೈಫ್ ದಿನಗಳು"
  },
  storageLocation: {
    en: "Storage Location",
    hi: "भंडारण स्थान",
    te: "నిల్వ స్థానం",
    ta: "சேமிப்பு இடம்",
    kn: "ಸಂಗ್ರಹ ಸ್ಥಳ"
  },
  riskLevel: {
    en: "Risk Level",
    hi: "जोखिम स्तर",
    te: "అపాయ మట్టం",
    ta: "ஆபத்து நிலை",
    kn: "ಅಪಾಯದ ಮಟ್ಟ"
  },

  // Risk Levels
  safe: {
    en: "SAFE",
    hi: "सुरक्षित",
    te: "సురక్షితం",
    ta: "பாதுகாப்பானது",
    kn: "ಸುರಕ್ಷಿತ"
  },
  risk: {
    en: "RISK",
    hi: "जोखिम",
    te: "అపాయం",
    ta: "ஆபத்து",
    kn: "ಅಪಾಯ"
  },
  high: {
    en: "HIGH",
    hi: "उच्च",
    te: "అధికం",
    ta: "உயர்",
    kn: "ಉನ್ನತ"
  },
  low: {
    en: "LOW",
    hi: "निम्न",
    te: "తక్కువ",
    ta: "குறைவு",
    kn: "ಕಡಿಮೆ"
  },
  medium: {
    en: "MEDIUM",
    hi: "मध्यम",
    te: "మధ్యస్థం",
    ta: "நடுத்தரம்",
    kn: "ಮಧ್ಯಮ"
  },
  good: {
    en: "Good",
    hi: "अच्छा",
    te: "మంచిది",
    ta: "நல்லது",
    kn: "ಒಳ್ಳೆಯದು"
  },
  moderate: {
    en: "Moderate",
    hi: "मध्यम",
    te: "మధ్యస్థం",
    ta: "நடுத்தரம்",
    kn: "ಮಧ್ಯಮ"
  },
  poor: {
    en: "Poor",
    hi: "खराब",
    te: "చెడ్డది",
    ta: "மோசமானது",
    kn: "ಕೆಟ್ಟದು"
  },
  delivered: {
    en: "Delivered",
    hi: "पहुंचाया गया",
    te: "చేరవేసినది",
    ta: "வழங்கப்பட்டது",
    kn: "ವಿತರಿಸಲಾಗಿದೆ"
  },
  pickupCompleted: {
    en: "Crop pickup completed",
    hi: "फसल उठान पूरा हुआ",
    te: "పంట పికప్ పూర్తయింది",
    ta: "பயிர் பிக்கப் முடிந்தது",
    kn: "ಬೆಳೆ ಪಿಕ್‌ಅಪ್ ಪೂರ್ಣವಾಗಿದೆ"
  },
  pickupRequested: {
    en: "Pickup requested",
    hi: "उठान का अनुरोध किया गया",
    te: "పికప్ కోరాము",
    ta: "பிக்கப் கேட்கப்பட்டது",
    kn: "ಪಿಕ್‌ಅಪ್ ವಿನಂತಿಸಲಾಗಿದೆ"
  },

  // Season Names
  zaid: {
    en: "Zaid",
    hi: "ज़ायद",
    te: "జాయిద్",
    ta: "சாயித்",
    kn: "ಜಾಯಿದ್"
  },
  kharif: {
    en: "Kharif",
    hi: "खरीफ",
    te: "ఖరీఫ్",
    ta: "கரீஃப்",
    kn: "ಖರೀಫ್"
  },
  rabi: {
    en: "Rabi",
    hi: "रबी",
    te: "రబీ",
    ta: "ரபி",
    kn: "ರಬಿ"
  },
  season: {
    en: "Season",
    hi: "मौसम",
    te: "ఋతువు",
    ta: "பருவம்",
    kn: "ಋತು"
  },

  // Alert Messages
  highSpoilageRisk: {
    en: "High spoilage risk. Immediate action required.",
    hi: "उच्च खराब होने का जोखिम। तत्काल कार्रवाई आवश्यक।",
    te: "అధిక చెడిపోయే అపాయం. వెంటనే చర్య అవసరం.",
    ta: "உயர் சிதைவு ஆபத்து. உடனடி நடவடிக்கை தேவை.",
    kn: "ಉನ್ನತ ಹಾಳಾಗುವ ಅಪಾಯ. ತಕ್ಷಣ ಕ್ರಮ ಅಗತ್ಯ."
  },
  freshnessDeclining: {
    en: "Crop freshness declining. Monitor closely.",
    hi: "फसल की ताजगी घट रही है। करीब से निगरानी करें।",
    te: "పంట తాజాదనం తగ్గుతోంది. సన్నిహితంగా పర్యవేక్షించండి.",
    ta: "பயிர் புதுமை குறைந்து வருகிறது. கவனமாக கண்காணிக்கவும்.",
    kn: "ಬೆಳೆಯ ತಾಜಾತನ ಕಡಿಮೆಯಾಗುತ್ತಿದೆ. ಹತ್ತಿರವಾಗಿ ಮೇಲ್ವಿಚಾರಣೆ ಮಾಡಿ."
  },
  good: {
    en: "Good",
    hi: "अच्छा",
    te: "బాగుంది",
    ta: "நல்லது",
    kn: "ಒಳ್ಳೆಯದು"
  },

  // Sections
  submittedBatchDetails: {
    en: "Submitted Batch Details",
    hi: "जमा किए गए बैच का विवरण",
    te: "సమర్పించిన బ్యాచ్ వివరాలు",
    ta: "சமர்ப்பிக்கப்பட்ட தொகுதி விவரங்கள்",
    kn: "ಸಲ್ಲಿಸಿದ ಬ್ಯಾಚ್ ವಿವರಗಳು"
  },
  recentlySubmitted: {
    en: "Recently submitted batch information",
    hi: "हाल ही में जमा किए गए बैच की जानकारी",
    te: "ఇటీవల సమర్పించిన బ్యాచ్ సమాచారం",
    ta: "சமர்ப்பிக்கப்பட்ட தொகுதி தகவல்",
    kn: "ಇತ್ತೀಚೆಗೆ ಸಲ್ಲಿಸಿದ ಬ್ಯಾಚ್ ಮಾಹಿತಿ"
  },
  storedCropDetails: {
    en: "Stored Crop Details",
    hi: "संग्रहीत फसल का विवरण",
    te: "నిల్వ ఉన్న పంట వివరాలు",
    ta: "சேமித்த பயிர் விவரங்கள்",
    kn: "ಸಂಗ್ರಹಿಸಿದ ಬೆಳೆಯ ವಿವರಗಳು"
  },
  viewStoredCropBatches: {
    en: "View your stored crop batches and their current status",
    hi: "अपने संग्रहीत फसल के बैच और उनकी वर्तमान स्थिति देखें",
    te: "మీ నిల్వ ఉన్న పంట బ్యాచ్‌లు మరియు వాటి ప్రస్తుత స్థితిని చూడండి",
    ta: "உங்கள் சேமித்த பயிர் தொகுதிகள் மற்றும் அவற்றின் தற்போதைய நிலையைக் காண்க",
    kn: "ನಿಮ್ಮ ಸಂಗ್ರಹಿಸಿದ ಬೆಳೆ ಬ್ಯಾಚ್‌ಗಳು ಮತ್ತು ಅವುಗಳ ಪ್ರಸ್ತುತ ಸ್ಥಿತಿಯನ್ನು ವೀಕ್ಷಿಸಿ"
  },

  // Crop Overview Panel
  cropOverview: {
    en: "Crop Overview",
    hi: "फसल का अवलोकन",
    te: "పంట సమీక్ష",
    ta: "பயிர் கண்ணோட்டம்",
    kn: "ಬೆಳೆಯ ಉದ್ದೇಶ"
  },

  // Freshness Panel
  freshnessPanel: {
    en: "Freshness",
    hi: "ताजगी",
    te: "తాజాదనం",
    ta: "புதுமை",
    kn: "ತಾಜಾತನ"
  },

  // Alerts Panel
  alertsPanel: {
    en: "Alerts",
    hi: "अलर्ट",
    te: "హెచ్చరికలు",
    ta: "எச்சரிக்கைகள்",
    kn: "ಎಚ್ಚರಿಕೆಗಳು"
  },

  // Warehouse Info Panel
  warehouseInfo: {
    en: "Warehouse Info",
    hi: "गोदाम की जानकारी",
    te: "గోదాము సమాచారం",
    ta: "கிடங்கு தகவல்",
    kn: "ಗೋದಾಮು ಮಾಹಿತಿ"
  },

  // AI Recommendations Panel
  aiRecommendation: {
    en: "AI Recommendation",
    hi: "एआई सिफारिश",
    te: "AI సిఫార్సు",
    ta: "AI பரிந்துரை",
    kn: "AI ಶಿಫಾರಸು"
  },

  // Empty States
  selectBatchToView: {
    en: "Select a batch from the table to view details.",
    hi: "विवरण देखने के लिए तालिका से एक बैच चुनें।",
    te: "వివరాలను చూడటానికి పట్టిక నుండి ఒక బ్యాచ్‌ను ఎంచుకోండి.",
    ta: "விவரங்களைக் காண பட்டியலிலிருந்து ஒரு தொகுதியைத் தேர்ந்தெடுக்கவும்.",
    kn: "ವಿವರಗಳನ್ನು ವೀಕ್ಷಿಸಲು ಪಟ್ಟಿಯಿಂದ ಒಂದು ಬ್ಯಾಚ್ ಅನ್ನು ಆಯ್ಕೆಮಾಡಿ."
  },

  // Success Messages
  batchSubmittedSuccess: {
    en: "Batch submitted successfully",
    hi: "बैच सफलतापूर्वक जमा किया गया",
    te: "బ్యాచ్ విజయవంతంగా సమర్పించబడింది",
    ta: "தொகுதி வெற்றிகரமாக சமர்ப்பிக்கப்பட்டது",
    kn: "ಬ್ಯಾಚ್ ಯಶಸ್ವಿಯಾಗಿ ಸಲ್ಲಿಸಲಾಗಿದೆ"
  },

  // AI Recommendation Translations
  recommendation: {
    en: "Recommendation",
    hi: "सिफारिश",
    te: "సిఫార్సు",
    ta: "பரிந்துரை",
    kn: "ಶಿಫಾರಸು"
  },
  explanation: {
    en: "Explanation",
    hi: "व्याख्या",
    te: "వివరణ",
    ta: "விளக்கம்",
    kn: "ವಿವರಣೆ"
  },
  outlook: {
    en: "Outlook",
    hi: "परिदृश्य",
    te: "అవుట్‌లుక్",
    ta: "கணிப்பு",
    kn: "ಔಟ್‌ಲುಕ್"
  },
  alert: {
    en: "Alert",
    hi: "चेतावनी",
    te: "హెచ్చరిక",
    ta: "எச்சரிக்கை",
    kn: "ಎಚ್ಚರಿಕೆ"
  },

  // Common AI Terms
  immediateAction: {
    en: "Immediate action required",
    hi: "तत्काल कार्रवाई आवश्यक",
    te: "వెంటనే చర్య అవసరం",
    ta: "உடனடி நடவடிக்கை தேவை",
    kn: "ತಕ್ಷಣ ಕ್ರಮ ಅಗತ್ಯ"
  },
  salvage: {
    en: "salvage",
    hi: "बचाव",
    te: "రక్షించు",
    ta: "மீட்பு",
    kn: "ರಕ್ಷಿಸು"
  },
  discard: {
    en: "discard",
    hi: "निपटान",
    te: "విస్మరించు",
    ta: "நிராகரி",
    kn: "ತ್ಯಜಿಸು"
  },
  dispatch: {
    en: "dispatch",
    hi: "प्रेषण",
    te: "పంపిణీ",
    ta: "அனுப்புதல்",
    kn: "ರವಾನೆ"
  },
  warehouseNotSuitable: {
    en: "Current warehouse conditions are not suitable",
    hi: "वर्तमान गोदाम की स्थितियाँ उपयुक्त नहीं हैं",
    te: "ప్రస్తుత గోదాము పరిస్థితులు అనుకూలంగా లేవు",
    ta: "தற்போதைய கிடங்கு நிலைமைகள் பொருத்தமானவை அல்ல",
    kn: "ಪ್ರಸ್ತುತ ಗೋದಾಮು ಪರಿಸ್ಥಿತಿಗಳು ಸೂಕ್ತವಾಗಿಲ್ಲ"
  },
  tempOutOfRange: {
    en: "Temperature is out of optimal range",
    hi: "तापमान इष्टतम सीमा से बाहर है",
    te: "ఉష్ణోగ్రత అనుకూల పరిధిలో లేదు",
    ta: "வெப்பநிலை உகந்த வரம்பிற்கு வெளியே உள்ளது",
    kn: "ತಾಪಮಾನ ಸೂಕ್ತ ಪರಿಧಿಯಲ್ಲಿ ಇಲ್ಲ"
  },
  humidityOutOfRange: {
    en: "Humidity is out of optimal range",
    hi: "आर्द्रता इष्टतम सीमा से बाहर है",
    te: "తేమ అనుకూల పరిధిలో లేదు",
    ta: "ஈரப்பதம் உகந்த வரம்பிற்கு வெளியே உள்ளது",
    kn: "ಆರ್ದ್ರತೆ ಸೂಕ್ತ ಪರಿಧಿಯಲ್ಲಿ ಇಲ್ಲ"
  },
  moveToSalvage: {
    en: "Move batch to salvage or discard immediately",
    hi: "बैच को बचाव या निपटान के लिए तुरंत स्थानांतरित करें",
    te: "బ్యాచ్‌ను వెంటనే రక్షించడానికి లేదా విస్మరించడానికి తరలించండి",
    ta: "தொகுதியை மீட்புக்கு அல்லது நிராகரிக்க உடனடியாக நகர்த்தவும்",
    kn: "ಬ್ಯಾಚ್‌ನ್ನು ರಕ್ಷಿಸಲು ಅಥವಾ ತ್ಯಜಿಸಲು ತಕ್ಷಣ ಸ್ಥಳಾಂತರಿಸಿ"
  },
  crossSafeThreshold: {
    en: "Crop has already crossed safe freshness threshold",
    hi: "फसल पहले ही सुरक्षित ताजगी सीमा पार कर चुकी है",
    te: "పంట ఇప్పటికే సురక్షిత తాజాదన మితిని దాటింది",
    ta: "பயிர் ஏற்கனவே பாதுகாப்பான புதுமை வரம்பைக் கடந்துவிட்டது",
    kn: "ಬೆಳೆ ಈಗಾಗಲೇ ಸುರಕ್ಷಿತ ತಾಜಾತನ ಮಿತಿಯನ್ನು ದಾಟಿದೆ"
  },

  // Language Selector
  selectLanguage: {
    en: "Select Language",
    hi: "भाषा चुनें",
    te: "భాష ఎంచుకోండి",
    ta: "மொழியைத் தேர்ந்தெடுக்கவும்",
    kn: "ಭಾಷೆಯನ್ನು ಆಯ್ಕೆಮಾಡಿ"
  },

  // Actions
  requestPickup: {
    en: "Request Pickup",
    hi: "पिकअप का अनुरोध करें",
    te: "పికప్ కోరండి",
    ta: "பிக்கப் கோரிக்கை",
    kn: "ಪಿಕಪ್ ವಿನಂತಿಸಿ"
  },
  selected: {
    en: "Selected",
    hi: "चयनित",
    te: "ఎంచుకున్నారు",
    ta: "தேர்ந்தெடுக்கப்பட்டது",
    kn: "ಆಯ್ಕೆಮಾಡಲಾಗಿದೆ"
  },
  selectCityFirst: {
    en: "Select City First",
    hi: "पहले शहर चुनें",
    te: "ముందుగా నగరాన్ని ఎంచుకోండి",
    ta: "முதலில் நகரத்தைத் தேர்ந்தெடுக்கவும்",
    kn: "ಮೊದಲು ನಗರವನ್ನು ಆಯ್ಕೆಮಾಡಿ"
  }
};
// Crop name translations (common Indian crops)
const CropTranslations = {
  'apple': { hi: 'सेब', te: 'ఆపిల్', ta: 'ஆப்பிள்', kn: 'ಆಪಲ್' },
  'banana': { hi: 'केला', te: 'అరటి', ta: 'வாழை', kn: 'ಬಾಳೆ' },
  'brinjal': { hi: 'बैंगन', te: 'వంకాయ', ta: 'கத்திரிக்காய்', kn: 'ಬದನೇಕಾಯಿ' },
  'cabbage': { hi: 'पत्ता गोभी', te: 'క్యాబేజీ', ta: 'முட்டைகோஸ்', kn: 'ಎಲೆಕೋಸು' },
  'cauliflower': { hi: 'फूलगोभी', te: 'కాలీఫ్లవర్', ta: 'காலிஃப்ளவர்', kn: 'ಹೂಕೋಸು' },
  'chilli': { hi: 'मिर्च', te: 'మిర్చి', ta: 'மிளகாய்', kn: 'ಮೆಣಸಿನಕಾಯಿ' },
  'cotton': { hi: 'कपास', te: 'పత్తి', ta: 'பருத்தி', kn: 'ಹತ್ತಿ' },
  'grapes': { hi: 'अंगूर', te: 'ద్రాక్ష', ta: 'திராட்சை', kn: 'ದ್ರಾಕ್ಷಿ' },
  'groundnut': { hi: 'मूंगफली', te: 'వేరుశనగ', ta: 'நிலக்கடலை', kn: 'ಕಡಲೆಕಾಯಿ' },
  'maize': { hi: 'मक्का', te: 'మొక్కజొన్న', ta: 'மக்காச்சோளம்', kn: 'ಮೆಕ್ಕೆಜೋಳ' },
  'mango': { hi: 'आम', te: 'మామిడి', ta: 'மாங்கனி', kn: 'ಮಾವು' },
  'onion': { hi: 'प्याज', te: 'ఉల్లిపాయ', ta: 'வெங்காயம்', kn: 'ಈರುಳ್ಳಿ' },
  'orange': { hi: 'संतरा', te: 'కమలా', ta: 'ஆரஞ்சு', kn: 'ಕಿತ್ತಳೆ' },
  'potato': { hi: 'आलू', te: 'బంగాళాదుంప', ta: 'உருளைக்கிழங்கு', kn: 'ಆಲೂಗಡ್ಡೆ' },
  'pulses': { hi: 'दालें', te: 'పప్పులు', ta: 'பருப்பு', kn: 'ಕಾಳುಗಳು' },
  'rice': { hi: 'चावल', te: 'బియ్యం', ta: 'அரிசி', kn: 'ಅಕ್ಕಿ' },
  'sugarcane': { hi: 'गन्ना', te: 'చెరకు', ta: 'கரும்பு', kn: 'ಕಬ್ಬು' },
  'tomato': { hi: 'टमाटर', te: 'టమాటో', ta: 'தக்காளி', kn: 'ಟೊಮೇಟೊ' },
  'wheat': { hi: 'गेहूं', te: 'గోధుమ', ta: 'கோதுமை', kn: 'ಗೋಧಿ' }
};

// City name translations (major Indian cities)
const CityTranslations = {
  'agra': { hi: 'आगरा', te: 'ఆగ్రా', ta: 'ஆக்ரா', kn: 'ಆಗ್ರಾ' },
  'agartala': { hi: 'अगरतला', te: 'అగర్తలా', ta: 'அகர்தலா', kn: 'ಅಗರ್ತಲಾ' },
  'ahmedabad': { hi: 'अहमदाबाद', te: 'అహ్మదాబాద్', ta: 'அகமதாபாத்', kn: 'ಅಹಮದಾಬಾದ್' },
  'aizawl': { hi: 'ऐजॉल', te: 'ఐజవాల్', ta: 'ஐஸ்வால்', kn: 'ಐಜವಾಲ್' },
  'ajmer': { hi: 'अजमेर', te: 'అజ్మీర్', ta: 'அஜ்மீர்', kn: 'ಅಜ್ಮೇರ್' },
  'aligarh': { hi: 'अलीगढ़', te: 'అలీగఢ్', ta: 'அலிகார்', kn: 'ಅಲಿಗಢ್' },
  'allahabad': { hi: 'इलाहाबाद', te: 'అలహాబాద్', ta: 'அலஹாபாத்', kn: 'ಅಲಹಾಬಾದ್' },
  'alappuzha': { hi: 'अलप्पु झा', te: 'ఆలప్పుళ', ta: 'ஆலப்புழா', kn: 'ಆಲಪ್ಪುಳ' },
  'amravati': { hi: 'अमरावती', te: 'అమరావతి', ta: 'அமராவதி', kn: 'ಅಮರಾವತಿ' },
  'amritsar': { hi: 'अमृतसर', te: 'అమృత్సర్', ta: 'அம்ரித்சர்', kn: 'ಅಮೃತ್‌ಸರ್' },
  'asansol': { hi: 'आसनसोल', te: 'ఆసన్సోల్', ta: 'அசன்சோல்', kn: 'ಆಸನ್‌ಸೋಲ್' },
  'aurangabad': { hi: 'औरंगाबाद', te: 'ఔరంగాబాద్', ta: 'ஔரங்காபாத்', kn: 'ಔರಂಗಾಬಾದ್' },
  'bengaluru': { hi: 'बेंगलुरु', te: 'బెంగళూరు', ta: 'பெங்களூர்', kn: 'ಬೆಂಗಳೂರು' },
  'bangalore': { hi: 'बेंगलुरु', te: 'బెంగళూరు', ta: 'பெங்களூர்', kn: 'ಬೆಂಗಳೂರು' },
  'bharatpur': { hi: 'भरतपुर', te: 'భరత్పూర్', ta: 'பரத்பூர்', kn: 'ಭರತ್‌ಪುರ್' },
  'bhilai': { hi: 'भिलाई', te: 'భిలాయి', ta: 'பிலாய்', kn: 'ಭಿಲಾಯ್' },
  'bhiwandi': { hi: 'भिवंडी', te: 'భివండి', ta: 'பிவண்டி', kn: 'ಭಿವಂಡಿ' },
  'bhopal': { hi: 'भोपाल', te: 'భోపాల్', ta: 'போபால்', kn: 'ಭೋಪಾಲ್' },
  'bhubaneswar': { hi: 'भुवनेश्वर', te: 'భువనేశ్వర్', ta: 'புவனேஸ்வர்', kn: 'ಭುವನೇಶ್ವರ' },
  'bikaner': { hi: 'बीकानेर', te: 'బీకానేర్', ta: 'பிகானேர்', kn: 'ಬೀಕಾನೇರ್' },
  'bilaspur': { hi: 'बिलासपुर', te: 'బిలాస్పూర్', ta: 'பிலாஸ்பூர்', kn: 'ಬಿಲಾಸ್ಪುರ್' },
  'brahmapur': { hi: 'ब्रह्मपुर', te: 'బ్రహ్మపూర్', ta: 'பிரம்மபுர்', kn: 'ಬ್ರಹ್ಮಪುರ್' },
  'chandigarh': { hi: 'चंडीगढ़', te: 'చండీగఢ్', ta: 'சண்டிகர்', kn: 'ಚಂಡೀಗಢ್' },
  'chennai': { hi: 'चेन्नई', te: 'చెన్నై', ta: 'சென்னை', kn: 'ಚೆನ್ನೈ' },
  'coimbatore': { hi: 'कोयंबटूर', te: 'కోయంబతూర్', ta: 'கோயம்புத்தூர்', kn: 'ಕೊಯಂಬತ್ತೂರು' },
  'cuttack': { hi: 'कटक', te: 'కటక్', ta: 'கட்டக்', kn: 'ಕಟಕ್' },
  'dehradun': { hi: 'देहरादून', te: 'డెహ్రాడూన్', ta: 'டேராடூன்', kn: 'ಡೆಹ್ರಾಡೂನ್' },
  'delhi': { hi: 'दिल्ली', te: 'ఢిల్లీ', ta: 'டெல்லி', kn: 'ದೆಹಲಿ' },
  'dhanbad': { hi: 'धनबाद', te: 'ధన్బాద్', ta: 'தன்பாத்', kn: 'ಧನ್‌ಬಾದ್' },
  'durgapur': { hi: 'दुर्गापुर', te: 'దుర్గాపూర్', ta: 'துர்காபூர்', kn: 'ದುರ್ಗಾಪುರ್' },
  'erode': { hi: 'ईरोड', te: 'ఈరోడ్', ta: 'ஈரோடு', kn: 'ಈರೋಡ್' },
  'faridabad': { hi: 'फरीदाबाद', te: 'ఫరీదాబాద్', ta: 'ஃபரிதாபாத்', kn: 'ಫರೀದಾಬಾದ್' },
  'firozabad': { hi: 'फिरोजाबाद', te: 'ఫిరోజాబాద్', ta: 'ஃபிரோஸாபாத்', kn: 'ಫಿರೋಜಾಬಾದ್' },
  'gangtok': { hi: 'गंगटोक', te: 'గంగ్టోక్', ta: 'காங்டாக்', kn: 'ಗಂಗ್ಟಾಕ್' },
  'gaya': { hi: 'गया', te: 'గయ', ta: 'கயா', kn: 'ಗಯಾ' },
  'ghaziabad': { hi: 'गाजियाबाद', te: 'గాజియాబాద్', ta: 'காசியாபாத்', kn: 'ಗಾಜಿಯಾಬಾದ್' },
  'gorakhpur': { hi: 'गोरखपुर', te: 'గోరఖ్పూర్', ta: 'கோரக்பூர்', kn: 'ಗೋರಖ್‌ಪುರ್' },
  'gulbarga': { hi: 'गुलबर्गा', te: 'గుల్బర్గా', ta: 'குல்பர்கா', kn: 'ಗುಲ್ಬರ್ಗಾ' },
  'guntur': { hi: 'गुंटूर', te: 'గుంటూరు', ta: 'குண்டூர்', kn: 'ಗುಂಟೂರು' },
  'gurugram': { hi: 'गुरुग्राम', te: 'గురుగ్రామ్', ta: 'குருகிராம்', kn: 'ಗುರುಗ್ರಾಮ್' },
  'guwahati': { hi: 'गुवाहाटी', te: 'గువహాటి', ta: 'குவஹாத்தி', kn: 'ಗುವಾಹಾತಿ' },
  'gwalior': { hi: 'ग्वालियर', te: 'గ్వాలియర్', ta: 'குவாலியர்', kn: 'ಗ್ವಾಲಿಯರ್' },
  'howrah': { hi: 'हावड़ा', te: 'హౌరా', ta: 'ஹவுரா', kn: 'ಹೌರಾ' },
  'hyderabad': { hi: 'हैदराबाद', te: 'హైదరాబాద్', ta: 'ஹைதராபாத்', kn: 'ಹೈದರಾಬಾದ್' },
  'imphal': { hi: 'इंफाल', te: 'ఇంఫాల్', ta: 'இம்பால்', kn: 'ಇಂಫಾಲ್' },
  'indore': { hi: 'इंदौर', te: 'ఇండోర్', ta: 'இந்தோர்', kn: 'ಇಂದೋರ್' },
  'itanagar': { hi: 'ईटानगर', te: 'ఇటానగర్', ta: 'இட்டாநகர்', kn: 'ಇಟಾನಗರ್' },
  'jabalpur': { hi: 'जबलपुर', te: 'జబల్పూర్', ta: 'ஜபல்பூர்', kn: 'ಜಬಲ್ಪುರ್' },
  'jaipur': { hi: 'जयपुर', te: 'జైపూర్', ta: 'ஜெய்ப்பூர்', kn: 'ಜೈಪುರ' },
  'jalandhar': { hi: 'जालंधर', te: 'జలంధర్', ta: 'ஜலந்தர்', kn: 'ಜಲಂಧರ್' },
  'jalgaon': { hi: 'जलगांव', te: 'జల్గావ్', ta: 'ஜல்கான்', kn: 'ಜಲ್‌ಗಾಂವ್' },
  'jammu': { hi: 'जम्मू', te: 'జమ్మూ', ta: 'ஜம்மு', kn: 'ಜಮ್ಮು' },
  'jamnagar': { hi: 'जामनगर', te: 'జామ్నగర్', ta: 'ஜாம்நகர்', kn: 'ಜಾಮ್‌ನಗರ್' },
  'jamshedpur': { hi: 'जमशेदपुर', te: 'జమ్షెద్పూర్', ta: 'ஜம்ஷெட்பூர்', kn: 'ಜಮ್‌ಶೆದ್‌ಪುರ್' },
  'jhansi': { hi: 'झांसी', te: 'ఝాన్సీ', ta: '஝ான்சி', kn: 'ಝಾನ್ಸಿ' },
  'jodhpur': { hi: 'जोधपुर', te: 'జోధ్పూర్', ta: 'ஜோத்பூர்', kn: 'ಜೋಧ್‌ಪುರ್' },
  'jorhat': { hi: 'जोरहाट', te: 'జోర్హాట్', ta: 'ஜோர்ஹாட்', kn: 'ಜೋರ್ಹಾಟ್' },
  'kakinada': { hi: 'काकीनाडा', te: 'కాకినాడ', ta: 'காக்கிநாடா', kn: 'ಕಾಕಿನಾಡ' },
  'kanpur': { hi: 'कानपुर', te: 'కాన్పూర్', ta: 'கான்பூர்', kn: 'ಕಾನ್ಪುರ್' },
  'kharagpur': { hi: 'खड़गपुर', te: 'ఖరగ్పూర్', ta: 'கரக்பூர்', kn: 'ಖರಗ್ಪುರ್' },
  'kochi': { hi: 'कोच्चि', te: 'కొచ్చి', ta: 'கொச்சி', kn: 'ಕೊಚ್ಚಿ' },
  'kohima': { hi: 'कोहिमा', te: 'కోహిమా', ta: 'கோகிமா', kn: 'ಕೋಹಿಮಾ' },
  'kolkata': { hi: 'कोलकाता', te: 'కోల్‌కతా', ta: 'கொல்கத்தா', kn: 'ಕೋಲ್ಕತ್ತಾ' },
  'kollam': { hi: 'कोल्लम', te: 'కొల్లం', ta: 'கொல்லம்', kn: 'ಕೊಲ್ಲಂ' },
  'kolhapur': { hi: 'कोल्हापुर', te: 'కోల్హాపూర్', ta: 'கோல்ஹாபுர்', kn: 'ಕೊಲ್ಹಾಪುರ್' },
  'kota': { hi: 'कोटा', te: 'కోటా', ta: 'கோட்டா', kn: 'ಕೋಟಾ' },
  'kozhikode': { hi: 'कोझिकोड', te: 'కోజికోడ్', ta: 'கோழிக்கோடு', kn: 'ಕೋಝಿಕೋಡ್' },
  'kurnool': { hi: 'कurnूल', te: 'కర్నూల్', ta: 'கர்நூல்', kn: 'ಕರ್ನೂಲ್' },
  'lucknow': { hi: 'लखनऊ', te: 'లక్నో', ta: 'லக்னோ', kn: 'ಲಕ್ನೋ' },
  'ludhiana': { hi: 'लुधियाना', te: 'లుధియానా', ta: 'லுதியானா', kn: 'ಲುಧಿಯಾನಾ' },
  'madurai': { hi: 'मदुरै', te: 'మదురై', ta: 'மதுரை', kn: 'ಮದುರೈ' },
  'mangaluru': { hi: 'मंगलुरु', te: 'మంగళూరు', ta: 'மங்களூர்', kn: 'ಮಂಗಳೂರು' },
  'meerut': { hi: 'मेरठ', te: 'మీరట్', ta: 'மீரட்', kn: 'ಮೀರತ್' },
  'moradabad': { hi: 'मुरादाबाद', te: 'మురాదాబాద్', ta: 'முராதாபாத்', kn: 'ಮುರಾದಾಬಾದ್' },
  'mumbai': { hi: 'मुंबई', te: 'ముంబై', ta: 'மும்பை', kn: 'ಮುಂಬೈ' },
  'mysuru': { hi: 'मैसूर', te: 'మైసూరు', ta: 'மைசூர்', kn: 'ಮೈಸೂರು' },
  'nagpur': { hi: 'नागपुर', te: 'నాగపూర్', ta: 'நாக்பூர்', kn: 'ನಾಗಪುರ್' },
  'hubballi': { hi: 'हुब्बल्ली', te: 'హుబ్బల్లి', ta: 'ஹுப்பள்ளி', kn: 'ಹುಬ್ಬಳ್ಳಿ' },
  'hubli': { hi: 'हुबली', te: 'హుబ్లీ', ta: 'ஹுப்பளி', kn: 'ಹುಬ್ಬಳ್ಳಿ' },
  'latur': { hi: 'लातूर', te: 'లాతూర్', ta: 'லாத்தூர்', kn: 'ಲಾತೂರು' },
  'leh': { hi: 'लेह', te: 'లేహ్', ta: 'லேह', kn: 'ಲೇಹ್' },
  'muzaffarpur': { hi: 'मुजफ्फरपुर', te: 'ముజఫ్ఫర్‌పూర్', ta: 'முசாஃபர்பூர்', kn: 'ಮುಝಫ್ಫರ್‌ಪುರ್' },
  'nanded': { hi: 'नांदेड़', te: 'నాందేడ్', ta: 'நான்டேட்', kn: 'ನಾಂಡೇಡ್' },
  'nashik': { hi: 'नासिक', te: 'నాసిక్', ta: 'நாசிக்', kn: 'ನಾಶಿಕ್' },
  'nellore': { hi: 'नेल्लोर', te: 'నెల్లూరు', ta: 'நெல்லூர்', kn: 'ನೆಲ್ಲೂರು' },
  'nizamabad': { hi: 'निजामाबाद', te: 'నిజామాబాద్', ta: 'நிஜாமாபாத்', kn: 'ನಿಜಾಮಾಬಾದ್' },
  'noida': { hi: 'नोएडा', te: 'నోయిడా', ta: 'நோய்டா', kn: 'ನೋಯ್ಡಾ' },
  'panaji': { hi: 'पणजी', te: 'పణజీ', ta: 'பணஜி', kn: 'ಪಣಜಿ' },
  'patna': { hi: 'पटना', te: 'పాట్నా', ta: 'பாட்னா', kn: 'ಪಾಟ್ನಾ' },
  'port blair': { hi: 'पोर्ट ब्लेयर', te: 'పోర్ట్ బ్లెయిర్', ta: 'போர்ட் ப்ளேர்', kn: 'ಪೋರ್ಟ್ ಬ್ಲೇರ್' },
  'puducherry': { hi: 'पुदुचेरी', te: 'పుదుచ్చేరి', ta: 'புதுச்சேரி', kn: 'ಪುದುಚ್ಚೇರಿ' },
  'pune': { hi: 'पुणे', te: 'పూణే', ta: 'புனே', kn: 'ಪುಣೆ' },
  'raipur': { hi: 'रायपुर', te: 'రాయ్‌పూర్', ta: 'ராய்ப்பூர்', kn: 'ರಾಯ್‌ಪುರ್' },
  'rajahmundry': { hi: 'राजमुंदरी', te: 'రాజమండ్రి', ta: 'ராஜமுந்திரி', kn: 'ರಾಜಮುಂದ್ರಿ' },
  'rajkot': { hi: 'राजकोट', te: 'రాజ్‌కోట్', ta: 'ராஜ்கோட்', kn: 'ರಾಜ್‌ಕೋಟ್' },
  'ranchi': { hi: 'रांची', te: 'రాంచీ', ta: 'ராஞ்சி', kn: 'ರಾಂಚಿ' },
  'rourkela': { hi: 'राउरकेला', te: 'రౌర్కెలా', ta: 'ரவுர்கேலா', kn: 'ರೌರ್ಕೆಲಾ' },
  'saharanpur': { hi: 'सहारनपुर', te: 'సహారన్‌పూర్', ta: 'சஹாரன்பூர்', kn: 'ಸಹಾರನ್‌ಪುರ್' },
  'salem': { hi: 'सलेम', te: 'సేలం', ta: 'சேலம்', kn: 'ಸೇಲಂ' },
  'sangli': { hi: 'सांगली', te: 'సాంగ్లీ', ta: 'சாங்க்ளி', kn: 'ಸಾಂಗ್ಲಿ' },
  'shillong': { hi: 'शिलांग', te: 'షిల్లాంగ్', ta: 'ஷில்லாங்', kn: 'ಶಿಲಾಂಗ್' },
  'shimla': { hi: 'शिमला', te: 'షిమ్లా', ta: 'சிம்லா', kn: 'ಶಿಮ್ಲಾ' },
  'siliguri': { hi: 'सिलीगुड़ी', te: 'సిలిగుడి', ta: 'சிலிகுரி', kn: 'ಸಿಲಿಗುಡಿ' },
  'solapur': { hi: 'सोलापुर', te: 'సోలాపూర్', ta: 'சோலாபூர்', kn: 'ಸೋಲಾಪುರ್' },
  'sonipat': { hi: 'सोनीपत', te: 'సోనీపట్', ta: 'சோனிபட்', kn: 'ಸೋನಿಪತ್' },
  'srinagar': { hi: 'श्रीनगर', te: 'శ్రీనగర్', ta: 'ஸ்ரீநகர்', kn: 'ಶ್ರೀನಗರ್' },
  'srikakulam': { hi: 'श्रीकाकुलम', te: 'శ్రీకాకుళం', ta: 'ஸ்ரீகாகுலம்', kn: 'ಶ್ರೀಕಾಕುಳಂ' },
  'surat': { hi: 'सूरत', te: 'సూరత్', ta: 'சூரத்', kn: 'ಸೂರತ್' },
  'thane': { hi: 'ठाणे', te: 'ఠాణే', ta: 'தானே', kn: 'ಠಾಣೆ' },
  'thanjavur': { hi: 'तंजावुर', te: 'తంజావూరు', ta: 'தஞ்சாவூர்', kn: 'ತಂಜಾವೂರು' },
  'thiruvananthapuram': { hi: 'तिरुवनंतपुरम', te: 'తిరువనంతపురం', ta: 'திருவனந்தபுரம்', kn: 'ತಿರುವನಂತಪುರಂ' },
  'thrissur': { hi: 'त्रिशूर', te: 'త్రిశ్శూర్', ta: 'திருச்சூர்', kn: 'ತ್ರಿಶ್ಶೂರ್' },
  'tiruchirappalli': { hi: 'तिरुचिरापल्ली', te: 'తిరుచిరాపళ్లి', ta: 'திருச்சிராப்பள்ளி', kn: 'ತಿರುಚಿರಾಪಳ್ಳಿ' },
  'tirunelveli': { hi: 'तिरुनेलवेली', te: 'తిరునెల్వేలి', ta: 'திருநெல்வேலி', kn: 'ತಿರುನೆಲ್ವೇಲಿ' },
  'tirupati': { hi: 'तिरुपति', te: 'తిరుపతి', ta: 'திருப்பதி', kn: 'ತಿರುಪತಿ' },
  'tiruppur': { hi: 'तिरुप्पूर', te: 'తిరుప్పూర్', ta: 'திருப்பூர்', kn: 'ತಿರುಪ್ಪೂರು' },
  'udaipur': { hi: 'उदयपुर', te: 'ఉదయ్‌పూర్', ta: 'உதய்பூர்', kn: 'ಉದಯ್‌ಪುರ್' },
  'udupi': { hi: 'उडुपी', te: 'ఉడుపి', ta: 'உடுப்பி', kn: 'ಉಡುಪಿ' },
  'ujjain': { hi: 'उज्जैन', te: 'ఉజ్జయిని', ta: 'உஜ்ஜைன்', kn: 'ಉಜ್ಜಯಿನಿ' },
  'vadodara': { hi: 'वडोदरा', te: 'వడోదరా', ta: 'வடோதரா', kn: 'ವಡೋದರಾ' },
  'varanasi': { hi: 'वाराणसी', te: 'వారణాసి', ta: 'வாரணாசி', kn: 'ವಾರಣಾಸಿ' },
  'vellore': { hi: 'वेल्लोर', te: 'వెల్లూరు', ta: 'வேலூர்', kn: 'ವೆಲ್ಲೂರು' },
  'vijayawada': { hi: 'विजयवाड़ा', te: 'విజయవాడ', ta: 'விஜயவாடா', kn: 'ವಿಜಯವಾಡ' },
  'visakhapatnam': { hi: 'विशाखापत्तनम', te: 'విశాఖపట్నం', ta: 'விசாகப்பட்டினம்', kn: 'ವಿಶಾಖಪಟ್ಟಣಂ' },
  'warangal': { hi: 'वारंगल', te: 'వరంగల్', ta: 'வாரங்கல்', kn: 'ವಾರಂಗಲ್' }
};

// Helper to translate crop names
function translateCropName(name, lang) {
  if (!name || lang === 'en') return name;
  const key = name.toLowerCase().trim();
  const translated = CropTranslations[key]?.[lang];
  console.log(`translateCropName: "${name}" -> key:"${key}" -> lang:${lang} -> "${translated || name}"`);
  return translated || name;
}

// Helper to translate city names
function translateCityName(name, lang) {
  if (!name || lang === 'en') return name;
  const key = name.toLowerCase().trim();
  const translated = CityTranslations[key]?.[lang];
  console.log(`translateCityName: "${name}" -> key:"${key}" -> lang:${lang} -> "${translated || name}"`);
  return translated || name;
}

// Helper function to get translation
function getText(key, lang) {
  if (!FarmerTranslations[key]) return key;
  return FarmerTranslations[key][lang] || FarmerTranslations[key]['en'] || key;
}

// Warehouse name translations
const WarehouseTranslations = {
  'Delhi Warehouse': {
    hi: 'दिल्ली गोदाम',
    te: 'ఢిల్లీ గోదాము',
    ta: 'டெல்லி கிடங்கு',
    kn: 'ದೆಹಲಿ ಗೋದಾಮು'
  },
  'Chandigarh Warehouse': {
    hi: 'चंडीगढ़ गोदाम',
    te: 'చండీగఢ్ గోదాము',
    ta: 'சண்டிகர் கிடங்கு',
    kn: 'ಚಂಡೀಗಢ್ ಗೋದಾಮು'
  },
  'Bengaluru Warehouse': {
    hi: 'बेंगलुरु गोदाम',
    te: 'బెంగళూరు గోదాము',
    ta: 'பெங்களூരു கிடங்கு',
    kn: 'ಬೆಂಗಳೂರು ಗೋದಾಮು'
  },
  'Hyderabad Warehouse': {
    hi: 'हैदराबाद गोदाम',
    te: 'హైదరాబాద్ గోదాము',
    ta: 'ஹைதராபாத் கிடங்கு',
    kn: 'ಹೈದರಾಬಾದ್ ಗೋದಾಮು'
  },
  'Kolkata Warehouse': {
    hi: 'कोलकाता गोदाम',
    te: 'కోల్‌కతా గోదాము',
    ta: 'கொல்கத்தா கிடங்கு',
    kn: 'ಕೋಲ್ಕತ್ತಾ ಗೋದಾಮು'
  },
  'Bhubaneswar Warehouse': {
    hi: 'भुवनेश्वर गोदाम',
    te: 'భువనేశ్వర్ గోదాము',
    ta: 'புவனேஸ்வர் கிடங்கு',
    kn: 'ಭುವನೇಶ್ವರ ಗೋದಾಮು'
  },
  'Mumbai Warehouse': {
    hi: 'मुंबई गोदाम',
    te: 'ముంబై గోదాము',
    ta: 'மும்பை கிடங்கு',
    kn: 'ಮುಂಬೈ ಗೋದಾಮು'
  },
  'Ahmedabad Warehouse': {
    hi: 'अहमदाबाद गोदाम',
    te: 'అహ్మదాబాద్ గోదాము',
    ta: 'அகமதாபாத் கிடங்கு',
    kn: 'ಅಹಮದಾಬಾದ್ ಗೋದಾಮು'
  },
  'Nagpur Central Warehouse': {
    hi: 'नागपुर केंद्रीय गोदाम',
    te: 'నాగపూర్ సెంట్రల్ గోదాము',
    ta: 'நாக்பூர் மத்திய கிடங்கு',
    kn: 'ನಾಗಪುರ್ ಸೆಂಟ್ರಲ್ ಗೋದಾಮು'
  }
};

// Storage type translations
const StorageTypeTranslations = {
  'DRY': { hi: 'सूखा', te: 'ఎండు', ta: 'உலர்', kn: 'ಒಣ' },
  'COLD': { hi: 'ठंडा', te: 'చల్లని', ta: 'குளிர்', kn: 'ಚilled' },
  'COLD+DRY': { hi: 'ठंडा+सूखा', te: 'చల్లని+ఎండు', ta: 'குளிர்+உலர்', kn: 'ಚilled+ಒಣ' },
  'DRY+COLD': { hi: 'सूखा+ठंडा', te: 'ఎండు+చల్లని', ta: 'உலர்+குளிர்', kn: 'ಒಣ+ಚilled' }
};

// Helper to translate warehouse display text
function translateWarehouseName(name, lang) {
  if (!name || lang === 'en') return name;
  
  // Extract base warehouse name and storage type
  const match = name.match(/^(.+?)\s*\((.+?)\)$/);
  if (!match) {
    // Just translate the name if no storage type in parentheses
    const translated = WarehouseTranslations[name]?.[lang];
    console.log(`translateWarehouseName (no parens): "${name}" -> lang:${lang} -> "${translated || name}"`);
    return translated || name;
  }
  
  const [_, warehouseName, storageType] = match;
  const translatedName = WarehouseTranslations[warehouseName]?.[lang] || warehouseName;
  const translatedStorage = StorageTypeTranslations[storageType]?.[lang] || storageType;
  const result = `${translatedName} (${translatedStorage})`;
  console.log(`translateWarehouseName: "${name}" -> warehouse:"${warehouseName}" storage:"${storageType}" -> "${result}"`);
  return result;
}

// Helper to translate season names
function translateSeasonName(name, lang) {
  if (!name || lang === 'en') return name;
  const key = name.toLowerCase().trim();
  const translated = FarmerTranslations[key]?.[lang];
  console.log(`translateSeasonName: "${name}" -> key:"${key}" -> lang:${lang} -> "${translated || name}"`);
  return translated || name;
}
