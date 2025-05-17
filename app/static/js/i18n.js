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
    'audio': '音频'
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
    'audio': 'Audio'
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
    'audio': 'オーディオ'
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
  let text = translations[currentLanguage][key] || translations['zh-CN'][key] || key;
  
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

// 导出函数
window.i18n = {
  init: initLanguage,
  change: changeLanguage,
  get: getTranslation,
  update: updatePageLanguage,
  getCurrentLanguage: () => currentLanguage
}; 