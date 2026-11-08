// Local language translations dictionary (English, Kannada, Hindi)
// Keep numbers, symbols, currency amounts unchanged.

export const translations = {
  en: {
    appName: 'PROFITPILOT',
    appSubtitle: 'FLY FOR PROFIT. LAND SAFE.',
    paperTradingBanner: 'PAPER TRADING — VIRTUAL MONEY ONLY',
    status: 'STATUS:',
    statusIdle: 'READY (IDLE)',
    statusRunning: 'RUNNING',
    statusStopped: 'STOPPED',
    statusCompleted: 'COMPLETED',
    istClock: 'TIME (IST):',
    equity: 'TOTAL CAPITAL:',
    pnl: 'PROFIT / LOSS:',
    symbolLabel: 'Stock Name (NSE)',
    customSymbolLabel: 'Enter Symbol',
    amountLabel: 'Investment Amount (₹)',
    stopLossLabel: 'Safety Limit (Stop-Loss %)',
    dateLabel: 'Select Trading Day',
    btnStart: 'START SIMULATION',
    btnKill: 'STOP ALL (KILL)',
    syntheticWarning: 'SIMULATED DATA: For practice only',
    realDataVerified: 'REAL MARKET DATA REPLAY',
    feedSource: 'Data Source:',
    
    // Summary Cards (Beginner Dashboard)
    currentPrice: 'Current Stock Price',
    marketDirection: 'Market Direction',
    directionUp: 'Price Going Up',
    directionDown: 'Price Going Down',
    directionSideways: 'Moving Sideways',
    directionUnclear: 'Scanning Market',
    
    currentRecommendation: 'Current Recommendation',
    actionBuy: 'BUY',
    actionSell: 'SELL',
    actionHold: 'HOLD',
    confidence: 'Confidence',
    suggestedAction: 'Suggested Action:',
    reasonTitle: 'Why this recommendation?',
    
    buySummaryText: 'Price is showing a possible upward opportunity.',
    buyActionText: 'Consider buying.',
    buyReasonText: 'Price movement and indicators support a buy signal.',
    
    sellSummaryText: 'Price is showing a possible downward movement.',
    sellActionText: 'Consider selling.',
    sellReasonText: 'The existing strategy has detected a sell condition.',
    
    holdSummaryText: 'No clear opportunity right now.',
    holdActionText: 'Wait and watch.',
    holdReasonText: 'Current conditions do not meet the buying or selling rules.',

    // Chart Controls & Indicators
    chartTitle: 'PRICE MOVEMENT (5-MINUTE CANDLES)',
    chartSubtitle: 'Real-time price candles with automatic trade signals',
    bullishLabel: 'Price Going Up',
    bearishLabel: 'Price Going Down',
    toggleAveragePrice: 'Average Price Indicator',
    toggleTodaysHigh: "Today's High",
    toggleTodaysLow: "Today's Low",
    stopLossTag: 'Safety Limit',
    tradeInspectorTitle: 'TRADE SIGNAL INSPECTOR',
    noTradesYet: 'No executed trades yet. The system is scanning market conditions.',
    inspectorTip: '💡 Click any BUY or SELL arrow on the chart to view its price, time, and reason.',

    // Signal Modal
    signalDetailsTitle: 'Signal Execution Details',
    signalType: 'Signal Type:',
    signalTime: 'Signal Time:',
    signalPrice: 'Signal Price:',
    signalQuantity: 'Shares Filled:',
    signalStopLoss: 'Safety Limit (Stop):',
    signalProfitLoss: 'Trade Result (P&L):',
    signalReason: 'Strategy Reason:',
    closeModal: 'Close',

    // Advanced Technical Section Toggle
    advancedToggleShow: 'Show Technical Details & Strategy Engine ▼',
    advancedToggleHide: 'Hide Technical Details ▲',
    advancedSectionTitle: 'TECHNICAL STRATEGY DETAILS & PORTFOLIO LEDGER',
    
    // Ledger labels
    availCash: '1. Available Cash',
    invested: '2. Invested',
    positions: '3. Open Positions',
    avgEntry: '4. Average Entry',
    marketPrice: '5. Current Price',
    unrealizedPnl: '6. Live P&L',
    realizedPnl: '7. Closed P&L',
    totalFees: '8. Total Fees',
    totalEquity: '9. Total Capital',
    returnPct: '10. Return %',

    // Summary at End
    summaryTitleDone: 'SESSION COMPLETED — PERFORMANCE SUMMARY',
    summaryTitleKilled: 'SIMULATION HALTED (KILL SWITCH ACTIVATED)',
    totalTrades: 'TOTAL TRADES',
    netPnl: 'NET RESULT (AFTER FEES)',
    benchmark: 'BUY & HOLD COMPARISON',
    finalCapital: 'FINAL CAPITAL',
    runAgain: '🔄 Run Another Simulation',

    // Kill Modal
    killModalTitle: 'Emergency Stop',
    killModalMsg: 'Are you sure? This will halt trading immediately and protect your current cash and holdings.',
    killCancel: 'Cancel',
    killConfirm: 'Yes, Stop Trading'
  },

  kn: {
    appName: 'ಪ್ರಾಫಿಟ್‌ಪೈಲಟ್',
    appSubtitle: 'ಲಾಭಕ್ಕಾಗಿ ಹಾರಾಟ. ಸುರಕ್ಷಿತ ಇಳಿಯುವಿಕೆ.',
    paperTradingBanner: 'ವರ್ಚುವಲ್ ಟ್ರೇಡಿಂಗ್ — ಕೇವಲ ನಕಲಿ ಹಣ (ಯಾವುದೇ ನೈಜ ಅಪಾಯವಿಲ್ಲ)',
    status: 'ಸ್ಥಿತಿ:',
    statusIdle: 'ಸಿದ್ಧವಾಗಿದೆ (IDLE)',
    statusRunning: 'ಚಾಲನೆಯಲ್ಲಿದೆ (RUNNING)',
    statusStopped: 'ನಿಲ್ಲಿಸಲಾಗಿದೆ (STOPPED)',
    statusCompleted: 'ಪೂರ್ಣಗೊಂಡಿದೆ (COMPLETED)',
    istClock: 'ಸಮಯ (IST):',
    equity: 'ಒಟ್ಟು ಬಂಡವಾಳ:',
    pnl: 'ಲಾಭ / ನಷ್ಟ:',
    symbolLabel: 'ಷೇರು ಹೆಸರು (NSE)',
    customSymbolLabel: 'ಷೇರು ಕೋಡ್ ಬರೆಯಿರಿ',
    amountLabel: 'ಹೂಡಿಕೆ ಮೊತ್ತ (₹)',
    stopLossLabel: 'ಸುರಕ್ಷತಾ ಮಿತಿ (ಸ್ಟಾಪ್-ಲಾಸ್ %)',
    dateLabel: 'ವ್ಯಾಪಾರದ ದಿನಾಂಕ',
    btnStart: 'ಪ್ರಾರಂಭಿಸಿ (START)',
    btnKill: 'ಎಲ್ಲವನ್ನೂ ನಿಲ್ಲಿಸಿ (STOP)',
    syntheticWarning: 'ಮಾದರಿ ಡೇಟಾ: ಕೇವಲ ಅಭ್ಯಾಸಕ್ಕಾಗಿ',
    realDataVerified: 'ನೈಜ ಮಾರುಕಟ್ಟೆ ಡೇಟಾ ಮರುಚಾಲನೆ',
    feedSource: 'ಡೇಟಾ ಮೂಲ:',

    // Summary Cards (Beginner Dashboard)
    currentPrice: 'ಪ್ರಸ್ತುತ ಷೇರು ಬೆಲೆ',
    marketDirection: 'ಮಾರುಕಟ್ಟೆ ದಿಕ್ಕು',
    directionUp: 'ಬೆಲೆ ಏರುತ್ತಿದೆ (Going Up)',
    directionDown: 'ಬೆಲೆ ಇಳಿಯುತ್ತಿದೆ (Going Down)',
    directionSideways: 'ಸಮತೋಲನದಲ್ಲಿದೆ (Moving Sideways)',
    directionUnclear: 'ಮಾರುಕಟ್ಟೆ ಪರಿಶೀಲಿಸಲಾಗುತ್ತಿದೆ',

    currentRecommendation: 'ಪ್ರಸ್ತುತ ಶಿಫಾರಸು',
    actionBuy: 'ಖರೀದಿಸಿ (BUY)',
    actionSell: 'ಮಾರಿ (SELL)',
    actionHold: 'ಕಾಯಿರಿ (HOLD)',
    confidence: 'ವಿಶ್ವಾಸಾರ್ಹತೆ',
    suggestedAction: 'ಸೂಚಿಸಲಾದ ಕ್ರಮ:',
    reasonTitle: 'ಈ ಶಿಫಾರಸಿಗೆ ಕಾರಣವೇನು?',

    buySummaryText: 'ಬೆಲೆಯು ಸಂಭಾವ್ಯ ಏರಿಕೆಯ ಉತ್ತಮ ಅವಕಾಶವನ್ನು ತೋರಿಸುತ್ತಿದೆ.',
    buyActionText: 'ಖರೀದಿಸಲು ಪರಿಗಣಿಸಿ.',
    buyReasonText: 'ಬೆಲೆಯ ಚಲನೆ ಮತ್ತು ಸೂಚಕಗಳು ಖರೀದಿ ಸಂಕೇತವನ್ನು ಬಲವಾಗಿ ಬೆಂಬಲಿಸುತ್ತಿವೆ.',

    sellSummaryText: 'ಬೆಲೆಯು ಸಂಭಾವ್ಯ ಇಳಿಕೆಯ ಚಲನೆಯನ್ನು ತೋರಿಸುತ್ತಿದೆ.',
    sellActionText: 'ಮಾರಾಟ ಮಾಡಲು ಪರಿಗಣಿಸಿ.',
    sellReasonText: 'ಅಸ್ತಿತ್ವದಲ್ಲಿರುವ ತಂತ್ರವು ಮಾರಾಟದ ಸ್ಥಿತಿಯನ್ನು ಪತ್ತೆಹಚ್ಚಿದೆ.',

    holdSummaryText: 'ಈಗ ಯಾವುದೇ ಸ್ಪಷ್ಟ ಅವಕಾಶವಿಲ್ಲ.',
    holdActionText: 'ಕಾದು ನೋಡಿ.',
    holdReasonText: 'ಪ್ರಸ್ತುತ ಪರಿಸ್ಥಿತಿಗಳು ಖರೀದಿ ಅಥವಾ ಮಾರಾಟದ ನಿಯಮಗಳನ್ನು ಪೂರೈಸುತ್ತಿಲ್ಲ.',

    // Chart Controls & Indicators
    chartTitle: 'ಬೆಲೆ ಚಲನೆ (5 ನಿಮಿಷಗಳ ಕ್ಯಾಂಡಲ್‌ಗಳು)',
    chartSubtitle: 'ಸ್ವಯಂಚಾಲಿತ ವ್ಯಾಪಾರ ಸಂಕೇತಗಳೊಂದಿಗೆ ನೈಜ ಸಮಯದ ಬೆಲೆ ಕ್ಯಾಂಡಲ್‌ಗಳು',
    bullishLabel: 'ಬೆಲೆ ಏರಿಕೆ',
    bearishLabel: 'ಬೆಲೆ ಇಳಿಕೆ',
    toggleAveragePrice: 'ಸರಾಸರಿ ಬೆಲೆ ಸೂಚಕ',
    toggleTodaysHigh: "ಇಂದಿನ ಗರಿಷ್ಠ",
    toggleTodaysLow: "ಇಂದಿನ ಕನಿಷ್ಠ",
    stopLossTag: 'ಸುರಕ್ಷತಾ ಮಿತಿ',
    tradeInspectorTitle: 'ವ್ಯಾಪಾರ ಸಂಕೇತ ಪರಿಶೀಲಕ',
    noTradesYet: 'ಇನ್ನೂ ಯಾವುದೇ ವ್ಯಾಪಾರ ನಡೆದಿಲ್ಲ. ವ್ಯವಸ್ಥೆಯು ಮಾರುಕಟ್ಟೆಯನ್ನು ಗಮನಿಸುತ್ತಿದೆ.',
    inspectorTip: '💡 ಬೆಲೆ, ಸಮಯ ಮತ್ತು ಕಾರಣವನ್ನು ನೋಡಲು ಚಾರ್ಟ್‌ನಲ್ಲಿರುವ ಯಾವುದೇ BUY ಅಥವಾ SELL ಬಾಣವನ್ನು ಕ್ಲಿಕ್ ಮಾಡಿ.',

    // Signal Modal
    signalDetailsTitle: 'ಸಂಕೇತ ವಿವರಗಳು',
    signalType: 'ಸಂಕೇತ ಪ್ರಕಾರ:',
    signalTime: 'ಸಂಕೇತ ಸಮಯ:',
    signalPrice: 'ಸಂಕೇತ ಬೆಲೆ:',
    signalQuantity: 'ಷೇರುಗಳ ಸಂಖ್ಯೆ:',
    signalStopLoss: 'ಸುರಕ್ಷತಾ ಮಿತಿ:',
    signalProfitLoss: 'ವ್ಯಾಪಾರದ ಫಲಿತಾಂಶ (P&L):',
    signalReason: 'ತಂತ್ರದ ಕಾರಣ:',
    closeModal: 'ಮುಚ್ಚಿ',

    // Advanced Technical Section Toggle
    advancedToggleShow: 'ತಾಂತ್ರಿಕ ವಿವರಗಳು ಮತ್ತು ಎಂಜಿನ್ ವೀಕ್ಷಿಸಿ ▼',
    advancedToggleHide: 'ತಾಂತ್ರಿಕ ವಿವರಗಳನ್ನು ಮರೆಮಾಡಿ ▲',
    advancedSectionTitle: 'ತಾಂತ್ರಿಕ ತಂತ್ರ ವಿವರಗಳು ಮತ್ತು ಪೋರ್ಟ್‌ಫೋಲಿಯೊ ಲೆಡ್ಜರ್',

    // Ledger labels
    availCash: '1. ಲಭ್ಯವಿರುವ ನಗದು',
    invested: '2. ಹೂಡಿಕೆ ಮಾಡಿದ ಮೊತ್ತ',
    positions: '3. ಪ್ರಸ್ತುತ ಷೇರುಗಳು',
    avgEntry: '4. ಸರಾಸರಿ ಖರೀದಿ ಬೆಲೆ',
    marketPrice: '5. ಮಾರುಕಟ್ಟೆ ಬೆಲೆ',
    unrealizedPnl: '6. ಪ್ರಸ್ತುತ ಲಾಭ/ನಷ್ಟ',
    realizedPnl: '7. ಅಂತಿಮ ಲಾಭ/ನಷ್ಟ',
    totalFees: '8. ಒಟ್ಟು ಶುಲ್ಕಗಳು',
    totalEquity: '9. ಒಟ್ಟು ಮೌಲ್ಯ',
    returnPct: '10. ಲಾಭದ ಶೇಕಡಾ %',

    // Summary at End
    summaryTitleDone: 'ಅಧಿವೇಶನ ಪೂರ್ಣಗೊಂಡಿದೆ — ಕಾರ್ಯಕ್ಷಮತೆಯ ಸಾರಾಂಶ',
    summaryTitleKilled: 'ವ್ಯಾಪಾರವನ್ನು ನಿಲ್ಲಿಸಲಾಗಿದೆ (ತುರ್ತು ಸ್ವಿಚ್ ಚಾಲಿತವಾಗಿದೆ)',
    totalTrades: 'ಒಟ್ಟು ವ್ಯಾಪಾರಗಳು',
    netPnl: 'ನಿವ್ವಳ ಲಾಭ/ನಷ್ಟ (ಶುಲ್ಕಗಳ ನಂತರ)',
    benchmark: 'ಖರೀದಿಸಿ ಇಟ್ಟುಕೊಂಡ ಫಲಿತಾಂಶ',
    finalCapital: 'ಅಂತಿಮ ಬಂಡವಾಳ',
    runAgain: '🔄 ಇನ್ನೊಂದು ಸಿಮ್ಯುಲೇಶನ್ ರನ್ ಮಾಡಿ',

    // Kill Modal
    killModalTitle: 'ತುರ್ತು ನಿಲುಗಡೆ',
    killModalMsg: 'ಖಚಿತವೇ? ಇದು ತಕ್ಷಣವೇ ವ್ಯಾಪಾರವನ್ನು ನಿಲ್ಲಿಸುತ್ತದೆ ಮತ್ತು ನಿಮ್ಮ ಪ್ರಸ್ತುತ ಬಂಡವಾಳವನ್ನು ಸಂರಕ್ಷಿಸುತ್ತದೆ.',
    killCancel: 'ರದ್ದುಮಾಡಿ',
    killConfirm: 'ಹೌದು, ವ್ಯಾಪಾರ ನಿಲ್ಲಿಸಿ'
  },

  hi: {
    appName: 'प्रॉफ़िटपायलट',
    appSubtitle: 'लाभ के लिए उड़ान। सुरक्षित लैंडिंग।',
    paperTradingBanner: 'पेपर ट्रेडिंग — केवल आभासी पैसा (कोई वास्तविक जोखिम नहीं)',
    status: 'स्थिति:',
    statusIdle: 'तैयार (IDLE)',
    statusRunning: 'चल रहा है (RUNNING)',
    statusStopped: 'रोक दिया गया (STOPPED)',
    statusCompleted: 'पूर्ण (COMPLETED)',
    istClock: 'समय (IST):',
    equity: 'कुल पूंजी:',
    pnl: 'लाभ / हानि:',
    symbolLabel: 'शेयर का नाम (NSE)',
    customSymbolLabel: 'शेयर कोड दर्ज करें',
    amountLabel: 'निवेश राशि (₹)',
    stopLossLabel: 'सुरक्षा सीमा (स्टॉप-लॉस %)',
    dateLabel: 'ट्रेडिंग की तारीख',
    btnStart: 'शुरू करें (START)',
    btnKill: 'सब रोकें (STOP)',
    syntheticWarning: 'सिम्युलेटेड डेटा: केवल अभ्यास के लिए',
    realDataVerified: 'वास्तविक बाजार डेटा रीप्ले',
    feedSource: 'डेटा स्रोत:',

    // Summary Cards (Beginner Dashboard)
    currentPrice: 'वर्तमान शेयर मूल्य',
    marketDirection: 'बाजार की दिशा',
    directionUp: 'कीमत बढ़ रही है (Going Up)',
    directionDown: 'कीमत गिर रही है (Going Down)',
    directionSideways: 'समतल चल रहा है (Moving Sideways)',
    directionUnclear: 'बाजार की जांच हो रही है',

    currentRecommendation: 'वर्तमान सिफारिश',
    actionBuy: 'खरीदें (BUY)',
    actionSell: 'बेचें (SELL)',
    actionHold: 'रुकें (HOLD)',
    confidence: 'विश्वास स्तर',
    suggestedAction: 'सुझाया गया कदम:',
    reasonTitle: 'इस सिफारिश का कारण क्या है?',

    buySummaryText: 'कीमत ऊपर जाने का एक संभावित अवसर दिखा रही है।',
    buyActionText: 'खरीदने पर विचार करें।',
    buyReasonText: 'मूल्य संचलन और तकनीकी संकेतक खरीद संकेत का समर्थन करते हैं।',

    sellSummaryText: 'कीमत नीचे जाने की संभावना दिखा रही है।',
    sellActionText: 'बेचने पर विचार करें।',
    sellReasonText: 'मौजूदा ट्रेडिंग रणनीति ने बिक्री की स्थिति का पता लगाया है।',

    holdSummaryText: 'अभी कोई स्पष्ट अवसर नहीं है।',
    holdActionText: 'रुकें और देखें।',
    holdReasonText: 'वर्तमान स्थितियां खरीदने या बेचने के नियमों को पूरा नहीं करती हैं।',

    // Chart Controls & Indicators
    chartTitle: 'मूल्य संचलन (5 मिनट की कैंडल)',
    chartSubtitle: 'स्वचालित ट्रेडिंग संकेतों के साथ रीयल-टाइम मूल्य चार्ट',
    bullishLabel: 'कीमत बढ़ना',
    bearishLabel: 'कीमत गिरना',
    toggleAveragePrice: 'औसत मूल्य संकेतक',
    toggleTodaysHigh: "आज का उच्चतम",
    toggleTodaysLow: "आज का न्यूनतम",
    stopLossTag: 'सुरक्षा सीमा',
    tradeInspectorTitle: 'ट्रेड सिग्नल विश्लेषक',
    noTradesYet: 'अभी तक कोई ट्रेड नहीं हुआ है। सिस्टम बाजार की निगरानी कर रहा है।',
    inspectorTip: '💡 मूल्य, समय और कारण देखने के लिए चार्ट पर किसी भी BUY या SELL तीर पर क्लिक करें।',

    // Signal Modal
    signalDetailsTitle: 'ट्रेड सिग्नल का पूरा विवरण',
    signalType: 'सिग्नल का प्रकार:',
    signalTime: 'सिग्नल का समय:',
    signalPrice: 'सिग्नल मूल्य:',
    signalQuantity: 'शेयरों की संख्या:',
    signalStopLoss: 'सुरक्षा सीमा (स्टॉप):',
    signalProfitLoss: 'ट्रेड परिणाम (P&L):',
    signalReason: 'रणनीति का कारण:',
    closeModal: 'बंद करें',

    // Advanced Technical Section Toggle
    advancedToggleShow: 'तकनीकी विवरण और स्ट्रैटेजी इंजन देखें ▼',
    advancedToggleHide: 'तकनीकी विवरण छुपाएं ▲',
    advancedSectionTitle: 'तकनीकी रणनीति विवरण और पोर्टफोलियो लेजर',

    // Ledger labels
    availCash: '1. उपलब्ध नकदी',
    invested: '2. निवेशित राशि',
    positions: '3. खुले शेयर',
    avgEntry: '4. औसत खरीद मूल्य',
    marketPrice: '5. वर्तमान मूल्य',
    unrealizedPnl: '6. वर्तमान लाभ/हानि',
    realizedPnl: '7. बंद लाभ/हानि',
    totalFees: '8. कुल शुल्क',
    totalEquity: '9. कुल पूंजी',
    returnPct: '10. रिटर्न %',

    // Summary at End
    summaryTitleDone: 'ट्रेडिंग सत्र पूर्ण — प्रदर्शन सारांश',
    summaryTitleKilled: 'ट्रेडिंग रोकी गई (आपातकालीन किल स्विच सक्रिय)',
    totalTrades: 'कुल ट्रेड',
    netPnl: 'शुद्ध लाभ/हानि (शुल्क के बाद)',
    benchmark: 'बाय और होल्ड से तुलना',
    finalCapital: 'अंतिम पूंजी',
    runAgain: '🔄 दूसरा सिमुलेशन चलाएं',

    // Kill Modal
    killModalTitle: 'आपातकालीन रोक (Emergency Stop)',
    killModalMsg: 'क्या आप सुनिश्चित हैं? यह तुरंत ट्रेडिंग रोक देगा और आपकी पूंजी और शेयरों को सुरक्षित रखेगा।',
    killCancel: 'रद्द करें',
    killConfirm: 'हां, ट्रेडिंग रोकें'
  }
};

