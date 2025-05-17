// 多语言支持
const translations = {
  // 中文翻译
  'zh-CN': {
    'app-title': '语音/视频转文字工具',
    'start-recording': '开始录音',
    'mic-recording': '麦克风录音',
    'import-file': '导入文件',
    'search-placeholder': '搜索',
    'all-files': '全部文件',
    'file-header': '文件',
    'operation-time': '操作时间',
    'duration': '时长',
    'actions': '操作',
    'status': '状态',
    'recognition-result': '识别结果',
    'click-to-view': '点击文件列表中的任务查看结果或进度',
    'copy-result': '复制结果',
    'clear-result': '清空结果区',
    'processing': '处理中...',
    'task-id': '任务ID',
    'file': '文件',
    'recognition-completed': '识别完成!',
    'settings': '设置',
    'recognition-language': '识别语言 (对新任务生效)',
    'api-key': 'Azure Speech API 密钥',
    'api-region': 'Azure 区域',
    'parallel-threads': '并行处理线程数',
    'segment-length': '音频分段长度 (秒)',
    'clean-temp': '清除临时文件',
    'test-api': '测试API连接',
    'cancel': '取消',
    'save-settings': '保存设置',
    'select-region': '-- 选择区域 --',
    'confirm-clean': '确定要清除所有临时文件和上传文件吗？此操作不会影响已完成的转写记录。',
    'cleaning': '清理中...',
    'download-txt': 'TXT',
    'download-audio': 'WAV',
    'delete-task': '删除任务',
    'confirm-delete': '确认删除',
    'confirm-delete-message': '确定要删除任务 "{0}" 吗？此操作不可撤销。',
    'delete': '删除',
    'no-summary': '暂无摘要',
    'no-tasks': '没有任务记录',
    'unknown-file': '未知文件',
    'unknown-time': '未知时间',
    'language-selector': '界面语言',
    'video': '视频',
    'audio': '音频',
    'checking-format': '检查文件格式...',
    'uploading': '上传中...',
    'api-settings-incomplete': '错误：API设置未完成。',
    'video-processing': '视频处理中，正在提取音频...',
    'audio-processing': '音频处理中...',
    'please-wait': '请耐心等待。',
    'no-recognition-result': '没有识别结果。',
    'error': '错误',
    'generating-txt': '正在生成文本文件...',
    'txt-generated': '已生成文本文件: {0}',
    'txt-generation-failed': '生成文本文件失败: {0}',
    'txt-generation-error': '生成TXT时出错',
    'download-started': '开始下载处理后的音频文件...',
    'task-deleted': '任务已删除。',
    'task-delete-failed': '删除任务失败。',
    'task-delete-network-error': '删除任务时发生网络错误或服务器错误。',
    'task-delete-unexpected-error': '删除任务时发生意外错误。',
    'api-key-region-empty': 'API密钥和区域不能为空。',
    'api-key-format-incorrect': 'API密钥格式不正确。',
    'region-format-incorrect': '区域格式不正确。',
    'settings-saved': '设置已保存。',
    'cleanup-complete': '清理完成！',
    'cleanup-failed': '清理失败',
    'cleanup-error': '清理文件时发生错误。',
    'file-needs-conversion': '文件需要转换',
    'file-conversion': '文件需要格式转换',
    'video-detected': '检测到您上传的是视频文件，需要提取音频才能进行识别。',
    'audio-conversion-needed': '检测到您上传的是音频文件，需要转换格式才能进行识别。',
    'file-name': '文件名: {0}',
    'preparing-conversion': '准备转换...',
    'conversion-error': '转换出错',
    'starting-conversion': '开始转换',
    'conversion-completed': '转换完成，可以开始识别。',
    'use-converted-file': '使用转换后的文件',
    'welcome-message': '欢迎使用！请先在设置中配置您的Azure API密钥和区域。',
    // 语言名称翻译
    'lang-zh-CN': '简体中文',
    'lang-zh-HK': '粤语/香港',
    'lang-zh-TW': '繁体中文',
    'lang-en-US': '英语/美国',
    'lang-en-GB': '英语/英国',
    'lang-ja-JP': '日语',
    'lang-ko-KR': '韩语',
    'lang-fr-FR': '法语',
    'lang-de-DE': '德语',
    'lang-es-ES': '西班牙语',
    'lang-it-IT': '意大利语',
    'lang-pt-BR': '葡萄牙语',
    'lang-ru-RU': '俄语'
  },
  
  // 英语翻译
  'en-US': {
    'app-title': 'Speech/Video to Text Tool',
    'start-recording': 'Start Recording',
    'mic-recording': 'Microphone Recording',
    'import-file': 'Import File',
    'search-placeholder': 'Search',
    'all-files': 'All Files',
    'file-header': 'File',
    'operation-time': 'Operation Time',
    'duration': 'Duration',
    'actions': 'Actions',
    'status': 'Status',
    'recognition-result': 'Recognition Result',
    'click-to-view': 'Click on a task in the list to view results or progress',
    'copy-result': 'Copy Result',
    'clear-result': 'Clear Result Area',
    'processing': 'Processing...',
    'task-id': 'Task ID',
    'file': 'File',
    'recognition-completed': 'Recognition Completed!',
    'settings': 'Settings',
    'recognition-language': 'Recognition Language (applies to new tasks)',
    'api-key': 'Azure Speech API Key',
    'api-region': 'Azure Region',
    'parallel-threads': 'Parallel Processing Threads',
    'segment-length': 'Audio Segment Length (seconds)',
    'clean-temp': 'Clean Temporary Files',
    'test-api': 'Test API Connection',
    'cancel': 'Cancel',
    'save-settings': 'Save Settings',
    'select-region': '-- Select Region --',
    'confirm-clean': 'Are you sure you want to clear all temporary files and uploads? This will not affect completed transcription records.',
    'cleaning': 'Cleaning...',
    'download-txt': 'TXT',
    'download-audio': 'WAV',
    'delete-task': 'Delete Task',
    'confirm-delete': 'Confirm Deletion',
    'confirm-delete-message': 'Are you sure you want to delete task "{0}"? This action cannot be undone.',
    'delete': 'Delete',
    'no-summary': 'No summary',
    'no-tasks': 'No task records',
    'unknown-file': 'Unknown file',
    'unknown-time': 'Unknown time',
    'language-selector': 'Interface Language',
    'video': 'Video',
    'audio': 'Audio',
    'checking-format': 'Checking file format...',
    'uploading': 'Uploading...',
    'api-settings-incomplete': 'Error: API settings are incomplete.',
    'video-processing': 'Processing video, extracting audio...',
    'audio-processing': 'Processing audio...',
    'please-wait': 'Please wait.',
    'no-recognition-result': 'No recognition result.',
    'error': 'Error',
    'generating-txt': 'Generating text file...',
    'txt-generated': 'Text file generated: {0}',
    'txt-generation-failed': 'Failed to generate text file: {0}',
    'txt-generation-error': 'Error generating TXT file',
    'download-started': 'Started downloading processed audio file...',
    'task-deleted': 'Task has been deleted.',
    'task-delete-failed': 'Failed to delete task.',
    'task-delete-network-error': 'Network or server error while deleting task.',
    'task-delete-unexpected-error': 'Unexpected error while deleting task.',
    'api-key-region-empty': 'API key and region cannot be empty.',
    'api-key-format-incorrect': 'API key format is incorrect.',
    'region-format-incorrect': 'Region format is incorrect.',
    'settings-saved': 'Settings saved.',
    'cleanup-complete': 'Cleanup complete!',
    'cleanup-failed': 'Cleanup failed',
    'cleanup-error': 'Error during file cleanup.',
    'file-needs-conversion': 'File Needs Conversion',
    'file-conversion': 'File format conversion required',
    'video-detected': 'Video file detected. Audio extraction is required for speech recognition.',
    'audio-conversion-needed': 'Audio file detected. Format conversion is required for speech recognition.',
    'file-name': 'File name: {0}',
    'preparing-conversion': 'Preparing conversion...',
    'conversion-error': 'Conversion error',
    'starting-conversion': 'Start Conversion',
    'conversion-completed': 'Conversion complete, ready for recognition.',
    'use-converted-file': 'Use Converted File',
    'welcome-message': 'Welcome! Please configure your Azure API key and region in the settings before using the tool.',
    // 语言名称翻译
    'lang-zh-CN': 'Chinese Simplified',
    'lang-zh-HK': 'Chinese (Cantonese/HK)',
    'lang-zh-TW': 'Chinese Traditional',
    'lang-en-US': 'English (US)',
    'lang-en-GB': 'English (UK)',
    'lang-ja-JP': 'Japanese',
    'lang-ko-KR': 'Korean',
    'lang-fr-FR': 'French',
    'lang-de-DE': 'German',
    'lang-es-ES': 'Spanish',
    'lang-it-IT': 'Italian',
    'lang-pt-BR': 'Portuguese',
    'lang-ru-RU': 'Russian'
  },
  
  // 日语翻译
  'ja-JP': {
    'app-title': '音声/ビデオをテキストに変換ツール',
    'start-recording': '録音開始',
    'mic-recording': 'マイク録音',
    'import-file': 'ファイルをインポート',
    'search-placeholder': '検索',
    'all-files': '全てのファイル',
    'file-header': 'ファイル',
    'operation-time': '操作時間',
    'duration': '長さ',
    'actions': 'アクション',
    'status': 'ステータス',
    'recognition-result': '認識結果',
    'click-to-view': 'タスクリストからタスクをクリックして結果や進捗を表示',
    'copy-result': '結果をコピー',
    'clear-result': '結果をクリア',
    'processing': '処理中...',
    'task-id': 'タスクID',
    'file': 'ファイル',
    'recognition-completed': '認識完了!',
    'settings': '設定',
    'recognition-language': '認識言語（新しいタスクに適用）',
    'api-key': 'Azure Speech APIキー',
    'api-region': 'Azureリージョン',
    'parallel-threads': '並列処理スレッド数',
    'segment-length': '音声セグメント長（秒）',
    'clean-temp': '一時ファイルをクリア',
    'test-api': 'API接続テスト',
    'cancel': 'キャンセル',
    'save-settings': '設定を保存',
    'select-region': '-- リージョンを選択 --',
    'confirm-clean': '一時ファイルとアップロードファイルをすべてクリアしてもよろしいですか？完了した変換記録には影響しません。',
    'cleaning': 'クリア中...',
    'download-txt': 'TXT',
    'download-audio': 'WAV',
    'delete-task': 'タスクを削除',
    'confirm-delete': '削除の確認',
    'confirm-delete-message': 'タスク「{0}」を削除してもよろしいですか？この操作は元に戻せません。',
    'delete': '削除',
    'no-summary': '要約なし',
    'no-tasks': 'タスク記録がありません',
    'unknown-file': '不明なファイル',
    'unknown-time': '不明な時間',
    'language-selector': 'インターフェース言語',
    'video': 'ビデオ',
    'audio': 'オーディオ',
    'checking-format': 'ファイル形式を確認中...',
    'uploading': 'アップロード中...',
    'api-settings-incomplete': 'エラー：API設定が不完全です。',
    'video-processing': 'ビデオ処理中、音声を抽出中...',
    'audio-processing': '音声処理中...',
    'please-wait': 'お待ちください。',
    'no-recognition-result': '認識結果がありません。',
    'error': 'エラー',
    'generating-txt': 'テキストファイルを生成中...',
    'txt-generated': 'テキストファイルが生成されました: {0}',
    'txt-generation-failed': 'テキストファイルの生成に失敗しました: {0}',
    'txt-generation-error': 'TXTファイルの生成中にエラーが発生しました',
    'download-started': '処理済み音声ファイルのダウンロードを開始しました...',
    'task-deleted': 'タスクが削除されました。',
    'task-delete-failed': 'タスクの削除に失敗しました。',
    'task-delete-network-error': 'タスクの削除中にネットワークまたはサーバーエラーが発生しました。',
    'task-delete-unexpected-error': 'タスクの削除中に予期しないエラーが発生しました。',
    'api-key-region-empty': 'APIキーとリージョンは空にできません。',
    'api-key-format-incorrect': 'APIキーの形式が正しくありません。',
    'region-format-incorrect': 'リージョンの形式が正しくありません。',
    'settings-saved': '設定が保存されました。',
    'cleanup-complete': 'クリーンアップ完了！',
    'cleanup-failed': 'クリーンアップに失敗しました',
    'cleanup-error': 'ファイルのクリーンアップ中にエラーが発生しました。',
    'file-needs-conversion': 'ファイル変換が必要',
    'file-conversion': 'ファイル形式の変換が必要',
    'video-detected': 'ビデオファイルが検出されました。音声認識のために音声抽出が必要です。',
    'audio-conversion-needed': '音声ファイルが検出されました。音声認識のために形式変換が必要です。',
    'file-name': 'ファイル名: {0}',
    'preparing-conversion': '変換の準備中...',
    'conversion-error': '変換エラー',
    'starting-conversion': '変換開始',
    'conversion-completed': '変換完了、認識の準備ができました。',
    'use-converted-file': '変換後のファイルを使用',
    'welcome-message': 'ようこそ！まずは設定でAzure APIキーとリージョンを設定してください。',
    // 语言名称翻译
    'lang-zh-CN': '中国語（簡体字）',
    'lang-zh-HK': '中国語（広東語/香港）',
    'lang-zh-TW': '中国語（繁体字）',
    'lang-en-US': '英語（アメリカ）',
    'lang-en-GB': '英語（イギリス）',
    'lang-ja-JP': '日本語',
    'lang-ko-KR': '韓国語',
    'lang-fr-FR': 'フランス語',
    'lang-de-DE': 'ドイツ語',
    'lang-es-ES': 'スペイン語',
    'lang-it-IT': 'イタリア語',
    'lang-pt-BR': 'ポルトガル語',
    'lang-ru-RU': 'ロシア語'
  }
};

// 当前语言
let currentLanguage = localStorage.getItem('uiLanguage') || 'zh-CN';

// 初始化语言
function initLanguage() {
  // 设置html的lang属性
  document.documentElement.lang = currentLanguage;
  
  // 设置页面标题
  document.title = translations[currentLanguage]['app-title'];
  
  // 更新所有带data-i18n属性的元素
  updatePageLanguage();
  
  // 更新语言选项
  updateLanguageOptions();
}

// 切换语言
function changeLanguage(lang) {
  if (translations[lang]) {
    currentLanguage = lang;
    localStorage.setItem('uiLanguage', lang);
    initLanguage();
  }
}

// 获取翻译文本
function getTranslation(key, ...params) {
  // 确保使用当前语言的翻译，如果不存在则回退到中文
  let text = translations[currentLanguage] && translations[currentLanguage][key] 
             ? translations[currentLanguage][key] 
             : (translations['zh-CN'] ? translations['zh-CN'][key] : key);
  
  // 处理参数替换 {0}, {1} 等
  if (params.length > 0) {
    params.forEach((param, index) => {
      text = text.replace(`{${index}}`, param);
    });
  }
  
  return text;
}

// 更新页面语言
function updatePageLanguage() {
  const elements = document.querySelectorAll('[data-i18n]');
  elements.forEach(el => {
    const key = el.getAttribute('data-i18n');
    
    if (key) {
      // 处理有属性的情况，如placeholder等
      if (key.includes(':')) {
        const [attr, textKey] = key.split(':');
        el.setAttribute(attr, getTranslation(textKey));
      } else {
        // 普通文本内容
        el.textContent = getTranslation(key);
      }
    }
  });
}

// 更新语言选项
function updateLanguageOptions() {
  // 更新识别语言下拉菜单中的语言名称
  const languageSelect = document.getElementById('languageModal');
  if (languageSelect) {
    Array.from(languageSelect.options).forEach(option => {
      const langCode = option.value;
      const langNameKey = 'lang-' + langCode;
      const localizedName = getTranslation(langNameKey);
      option.textContent = `${langCode} (${localizedName})`;
    });
  }
}

// 导出函数
window.i18n = {
  init: initLanguage,
  change: changeLanguage,
  get: getTranslation,
  update: updatePageLanguage,
  updateLanguageOptions: updateLanguageOptions,
  getCurrentLanguage: () => currentLanguage
}; 