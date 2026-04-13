# HTML 模板直接内嵌，避免 Docker COPY 路径问题
# 模板文件: templates/index.html

INDEX_HTML = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>BabyBus 下载器 v{{version}}</title>
    <style>
        *{margin:0;padding:0;box-sizing:border-box}
        body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;background:#f5f5f5;color:#333;line-height:1.6}
        .container{max-width:1200px;margin:0 auto;padding:20px}
        header{background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);color:white;padding:30px;border-radius:12px;margin-bottom:20px}
        header h1{font-size:28px;margin-bottom:8px}
        header p{opacity:.9}
        .nav{display:flex;gap:10px;margin-bottom:20px;flex-wrap:wrap}
        .nav a{padding:10px 20px;background:white;border-radius:8px;text-decoration:none;color:#667eea;font-weight:500;box-shadow:0 2px 4px rgba(0,0,0,.1)}
        .nav a:hover{background:#f0f0f0}
        .nav a.active{background:#667eea;color:white}
        .stats-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:15px;margin-bottom:20px}
        .stat-card{background:white;padding:20px;border-radius:12px;box-shadow:0 2px 8px rgba(0,0,0,.08)}
        .stat-card h3{font-size:14px;color:#666;text-transform:uppercase;margin-bottom:8px}
        .stat-card .number{font-size:32px;font-weight:bold;color:#667eea}
        .panel{background:white;padding:20px;border-radius:12px;box-shadow:0 2px 8px rgba(0,0,0,.08);margin-bottom:20px}
        .panel h2{font-size:18px;margin-bottom:15px;color:#333}
        .status-badge{display:inline-block;padding:6px 12px;border-radius:20px;font-size:12px;font-weight:500}
        .status-running{background:#d4edda;color:#155724}
        .status-idle{background:#e2e3e5;color:#383d41}
        .btn{padding:10px 20px;border:none;border-radius:8px;cursor:pointer;font-size:14px;font-weight:500;transition:all .2s;background:#667eea;color:white}
        .btn:hover{background:#5a6fd6}
        .btn:disabled{opacity:.6;cursor:not-allowed}
        .form-group{display:flex;gap:10px;margin-bottom:15px}
        .form-group input{flex:1;padding:10px 15px;border:1px solid #ddd;border-radius:8px;font-size:14px}
        .log-box{background:#1e1e1e;color:#d4d4d4;padding:15px;border-radius:8px;font-family:Consolas,monospace;font-size:13px;max-height:300px;overflow-y:auto;white-space:pre-wrap}
        .config-row{display:flex;justify-content:space-between;padding:10px 0;border-bottom:1px solid #eee}
        .config-row:last-child{border-bottom:none}
        .config-row span:first-child{color:#666}
        .result-box{margin-top:10px;padding:10px;background:#f8f9fa;border-radius:6px;font-size:13px}
    </style>
</head>
<body>
<div class="container">
    <header><h1>🚌 BabyBus 下载器</h1><p>版本 {{version}} | Web 管理界面</p></header>
    <nav class="nav">
        <a href="/" class="active">仪表盘</a>
        <a href="/videos">视频列表</a>
        <a href="/files">文件管理</a>
        <a href="/logs">实时日志</a>
    </nav>
    <div class="stats-grid">
        <div class="stat-card"><h3>频道视频总数</h3><div class="number">{{stats.total_videos}}</div></div>
        <div class="stat-card"><h3>已下载</h3><div class="number">{{stats.downloaded}}</div></div>
        <div class="stat-card"><h3>待下载</h3><div class="number">{{stats.pending}}</div></div>
        <div class="stat-card"><h3>本地文件</h3><div class="number">{{stats.output_files}}</div></div>
        <div class="stat-card"><h3>短视频(&lt;3min)</h3><div class="number">{{stats.short_videos}}</div></div>
    </div>
    <div class="panel">
        <h2>运行状态</h2>
        <p>状态:
            {% if state.running %}
                <span class="status-badge status-running">运行中</span>
                <span style="margin-left:10px;color:#666">{{state.current_task}}</span>
            {% else %}
                <span class="status-badge status-idle">空闲</span>
            {% endif %}
        </p>
        {% if state.last_run %}<p style="color:#666;font-size:14px;margin-top:8px">上次运行: {{state.last_run}}</p>{% endif %}
        {% if state.last_result %}<div class="result-box">结果: {{state.last_result}}</div>{% endif %}
    </div>
    <div class="panel">
        <h2>手动下载</h2>
        <form class="form-group" onsubmit="return downloadVideo(event)">
            <input type="text" id="videoId" placeholder="输入 YouTube Video ID (如: dQw4w9WgXcQ)" required>
            <button type="submit" class="btn" id="dlBtn">开始下载</button>
        </form>
        <button class="btn" onclick="scanChannel()" id="scanBtn">扫描频道</button>
    </div>
    <div class="panel">
        <h2>配置信息</h2>
        <div class="config-row"><span>频道 URL</span><span>{{config.channel_url}}</span></div>
        <div class="config-row"><span>每次下载限制</span><span>{{config.max_downloads}} 个</span></div>
        <div class="config-row"><span>扫描间隔</span><span>{{config.interval_hours}} 小时</span></div>
    </div>
</div>
<script>
async function downloadVideo(e){
    e.preventDefault();
    var id=document.getElementById('videoId').value.trim();if(!id)return;
    var btn=document.getElementById('dlBtn');btn.disabled=true;btn.textContent='下载中...';
    try{
        var fd=new FormData();fd.append('video_id',id);
        var r=await fetch('/api/download',{method:'POST',body:fd});
        var d=await r.json();alert(d.message||d.error||JSON.stringify(d));
    }catch(err){alert('请求失败: '+err)}finally{btn.disabled=false;btn.textContent='开始下载'}
}
async function scanChannel(){
    var btn=document.getElementById('scanBtn');btn.disabled=true;btn.textContent='扫描中...';
    try{
        var r=await fetch('/api/scan',{method:'POST'});
        var d=await r.json();alert(d.message||d.error||JSON.stringify(d));
    }catch(err){alert('请求失败: '+err)}finally{btn.disabled=false;btn.textContent='扫描频道'}
}
setInterval(async function(){
    var r=await fetch('/api/status');
    var d=await r.json();
    var badge=document.querySelector('.status-badge');
    if(d.running&&badge){badge.className='status-badge status-running';badge.textContent='运行中';}
    else if(badge){badge.className='status-badge status-idle';badge.textContent='空闲';}
},5000);
</script>
</body>
</html>"""

VIDEOS_HTML = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width,initial-scale=1.0">
    <title>视频列表 - BabyBus 下载器</title>
    <style>
        *{margin:0;padding:0;box-sizing:border-box}
        body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;background:#f5f5f5;color:#333}
        .container{max-width:1200px;margin:0 auto;padding:20px}
        header{background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);color:white;padding:20px 30px;border-radius:12px;margin-bottom:20px}
        header h1{font-size:24px}
        .nav{display:flex;gap:10px;margin-bottom:20px;flex-wrap:wrap}
        .nav a{padding:10px 20px;background:white;border-radius:8px;text-decoration:none;color:#667eea;font-weight:500;box-shadow:0 2px 4px rgba(0,0,0,.1)}
        .nav a:hover{background:#f0f0f0}
        .nav a.active{background:#667eea;color:white}
        .filter-bar{display:flex;gap:10px;margin-bottom:20px;flex-wrap:wrap}
        .filter-bar a{padding:8px 16px;background:white;border-radius:20px;text-decoration:none;color:#666;font-size:14px}
        .filter-bar a.active{background:#667eea;color:white}
        .video-list{background:white;border-radius:12px;box-shadow:0 2px 8px rgba(0,0,0,.08);overflow:hidden}
        .video-item{display:flex;align-items:center;padding:15px 20px;border-bottom:1px solid #eee;gap:15px}
        .video-item:last-child{border-bottom:none}
        .video-item:hover{background:#f8f9fa}
        .video-thumb{width:120px;height:68px;background:#ddd;border-radius:6px;flex-shrink:0;overflow:hidden}
        .video-thumb img{width:100%;height:100%;object-fit:cover}
        .video-info{flex:1;min-width:0}
        .video-title{font-weight:500;margin-bottom:4px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
        .video-meta{font-size:13px;color:#666}
        .video-badges{display:flex;gap:6px;flex-wrap:wrap}
        .badge{padding:4px 10px;border-radius:12px;font-size:11px;font-weight:500}
        .badge-downloaded{background:#d4edda;color:#155724}
        .badge-pending{background:#fff3cd;color:#856404}
        .badge-short{background:#cce5ff;color:#004085}
        .btn-small{padding:6px 12px;border:none;border-radius:6px;cursor:pointer;font-size:12px;background:#667eea;color:white;text-decoration:none}
        .btn-small:hover{background:#5a6fd6}
        .empty-state{text-align:center;padding:60px 20px;color:#666}
    </style>
</head>
<body>
<div class="container">
    <header><h1>🎬 视频列表</h1></header>
    <nav class="nav">
        <a href="/">仪表盘</a><a href="/videos" class="active">视频列表</a>
        <a href="/files">文件管理</a><a href="/logs">实时日志</a>
    </nav>
    <div class="filter-bar">
        <a href="/videos?filter=all" class="{%if filter=='all'%}active{%endif%}">全部({{total}})</a>
        <a href="/videos?filter=downloaded" class="{%if filter=='downloaded'%}active{%endif%}">已下载</a>
        <a href="/videos?filter=pending" class="{%if filter=='pending'%}active{%endif%}">待下载</a>
        <a href="/videos?filter=short" class="{%if filter=='short'%}active{%endif%}">短视频</a>
    </div>
    <div class="video-list">
        {% for v in videos %}
        <div class="video-item">
            <div class="video-thumb">
                <img src="https://i.ytimg.com/vi/{{v.id}}/mqdefault.jpg"
                     alt="preview" onerror="this.style.display='none';this.parentElement.textContent='无预览'">
            </div>
            <div class="video-info">
                <div class="video-title">{{v.title}}</div>
                <div class="video-meta">ID: {{v.id}} | 时长: {{v.duration_fmt}} | 上传: {{v.upload_date}}</div>
            </div>
            <div class="video-badges">
                {% if v.downloaded %}<span class="badge badge-downloaded">已下载</span>
                {% else %}<span class="badge badge-pending">待下载</span>{% endif %}
                {% if v.is_short %}<span class="badge badge-short">短视频</span>{% endif %}
            </div>
            <div class="video-actions">
                <a href="https://youtube.com/watch?v={{v.id}}" target="_blank" class="btn-small">观看</a>
                {% if not v.downloaded %}
                <button class="btn-small" onclick="download('{{v.id}}')">下载</button>
                {% endif %}
            </div>
        </div>
        {% else %}
        <div class="empty-state"><p>暂无视频数据</p></div>
        {% endfor %}
    </div>
</div>
<script>
async function download(id){
    if(!confirm('确定要下载这个视频吗?'))return;
    var fd=new FormData();fd.append('video_id',id);
    try{
        var r=await fetch('/api/download',{method:'POST',body:fd});
        var d=await r.json();alert(d.message||d.error||JSON.stringify(d));
    }catch(err){alert('请求失败: '+err)}
}
</script>
</body>
</html>"""

FILES_HTML = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width,initial-scale=1.0">
    <title>文件管理 - BabyBus 下载器</title>
    <style>
        *{margin:0;padding:0;box-sizing:border-box}
        body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;background:#f5f5f5;color:#333}
        .container{max-width:1200px;margin:0 auto;padding:20px}
        header{background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);color:white;padding:20px 30px;border-radius:12px;margin-bottom:20px}
        header h1{font-size:24px}
        .nav{display:flex;gap:10px;margin-bottom:20px;flex-wrap:wrap}
        .nav a{padding:10px 20px;background:white;border-radius:8px;text-decoration:none;color:#667eea;font-weight:500;box-shadow:0 2px 4px rgba(0,0,0,.1)}
        .nav a:hover{background:#f0f0f0}
        .nav a.active{background:#667eea;color:white}
        .stats-bar{display:flex;gap:20px;margin-bottom:20px;padding:15px 20px;background:white;border-radius:12px;box-shadow:0 2px 8px rgba(0,0,0,.08)}
        .stats-bar div{font-size:14px}
        .stats-bar strong{color:#667eea;font-size:18px}
        .file-list{background:white;border-radius:12px;box-shadow:0 2px 8px rgba(0,0,0,.08);overflow:hidden}
        .file-item{display:flex;align-items:center;padding:15px 20px;border-bottom:1px solid #eee;gap:15px}
        .file-item:last-child{border-bottom:none}
        .file-item:hover{background:#f8f9fa}
        .file-icon{width:40px;height:40px;background:#667eea;border-radius:8px;display:flex;align-items:center;justify-content:center;color:white;font-size:18px;flex-shrink:0}
        .file-info{flex:1;min-width:0}
        .file-name{font-weight:500;margin-bottom:4px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
        .file-meta{font-size:13px;color:#666}
        .file-category{padding:4px 12px;background:#e9ecef;border-radius:12px;font-size:12px;color:#495057}
        .file-size{font-weight:500;color:#667eea;min-width:80px;text-align:right}
        .btn-small{padding:6px 12px;border:none;border-radius:6px;cursor:pointer;font-size:12px;background:#28a745;color:white;text-decoration:none}
        .btn-small:hover{background:#218838}
        .empty-state{text-align:center;padding:60px 20px;color:#666}
        .category-filter{display:flex;gap:8px;margin-bottom:15px;flex-wrap:wrap}
        .category-filter span{padding:6px 12px;background:white;border-radius:16px;font-size:13px;cursor:pointer}
        .category-filter span:hover{background:#e9ecef}
    </style>
</head>
<body>
<div class="container">
    <header><h1>📁 文件管理</h1></header>
    <nav class="nav">
        <a href="/">仪表盘</a><a href="/videos">视频列表</a>
        <a href="/files" class="active">文件管理</a><a href="/logs">实时日志</a>
    </nav>
    <div class="stats-bar">
        <div>总文件数: <strong>{{files|length}}</strong></div>
        <div>分类数: <strong>{{categories|length}}</strong></div>
        <div>总大小: <strong>{{total_size}} MB</strong></div>
    </div>
    {% if categories %}
    <div class="category-filter">
        <span onclick="filterCat('all')">全部</span>
        {% for cat in categories %}
        <span onclick="filterCat('{{cat}}')">{{cat}}</span>
        {% endfor %}
    </div>
    {% endif %}
    <div class="file-list" id="fileList">
        {% for f in files %}
        <div class="file-item" data-cat="{{f.category}}">
            <div class="file-icon">🎬</div>
            <div class="file-info">
                <div class="file-name">{{f.name}}</div>
                <div class="file-meta">{{f.mtime}} | {{f.path}}</div>
            </div>
            <span class="file-category">{{f.category}}</span>
            <span class="file-size">{{f.size_mb}} MB</span>
            <div class="file-actions">
                <a href="/download/{{f.path|encode}}" class="btn-small">下载</a>
            </div>
        </div>
        {% else %}
        <div class="empty-state"><p>暂无下载文件</p><p style="font-size:14px;margin-top:10px">去"视频列表"页面下载一些视频吧</p></div>
        {% endfor %}
    </div>
</div>
<script>
function filterCat(cat){
    var items=document.querySelectorAll('.file-item');
    items.forEach(function(i){
        i.style.display=(cat==='all'||i.dataset.cat===cat)?'flex':'none';
    });
}
</script>
</body>
</html>"""

LOGS_HTML = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width,initial-scale=1.0">
    <title>实时日志 - BabyBus 下载器</title>
    <style>
        *{margin:0;padding:0;box-sizing:border-box}
        body{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;background:#f5f5f5;color:#333}
        .container{max-width:1200px;margin:0 auto;padding:20px}
        header{background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);color:white;padding:20px 30px;border-radius:12px;margin-bottom:20px}
        header h1{font-size:24px}
        .nav{display:flex;gap:10px;margin-bottom:20px;flex-wrap:wrap}
        .nav a{padding:10px 20px;background:white;border-radius:8px;text-decoration:none;color:#667eea;font-weight:500;box-shadow:0 2px 4px rgba(0,0,0,.1)}
        .nav a:hover{background:#f0f0f0}
        .nav a.active{background:#667eea;color:white}
        .log-container{background:#1e1e1e;border-radius:12px;overflow:hidden}
        .log-header{display:flex;justify-content:space-between;align-items:center;padding:15px 20px;background:#2d2d2d;border-bottom:1px solid #3d3d3d}
        .log-header h2{color:#fff;font-size:16px;font-weight:500}
        .log-actions{display:flex;gap:10px}
        .btn{padding:6px 14px;border:none;border-radius:6px;cursor:pointer;font-size:12px;background:#667eea;color:white}
        .btn:hover{background:#5a6fd6}
        .btn-secondary{background:#6c757d}
        .btn-secondary:hover{background:#5a6268}
        .log-content{padding:15px 20px;font-family:Consolas,Monaco,monospace;font-size:13px;line-height:1.8;max-height:70vh;overflow-y:auto;white-space:pre-wrap;word-break:break-all}
        .log-line{color:#d4d4d4;margin-bottom:2px}
        .log-line .ts{color:#6cc644}
        .status-bar{display:flex;justify-content:space-between;align-items:center;padding:10px 20px;background:#2d2d2d;border-top:1px solid #3d3d3d;color:#888;font-size:12px}
        .status-indicator{display:flex;align-items:center;gap:8px}
        .status-dot{width:8px;height:8px;border-radius:50%;background:#28a745}
        .status-dot.running{background:#ffc107;animation:pulse 1s infinite}
        @keyframes pulse{0%,100%{opacity:1}50%{opacity:.5}}
        .empty-log{color:#666;text-align:center;padding:40px}
    </style>
</head>
<body>
<div class="container">
    <header><h1>📋 实时日志</h1></header>
    <nav class="nav">
        <a href="/">仪表盘</a><a href="/videos">视频列表</a>
        <a href="/files">文件管理</a><a href="/logs" class="active">实时日志</a>
    </nav>
    <div class="log-container">
        <div class="log-header">
            <h2>应用日志</h2>
            <div class="log-actions">
                <button class="btn btn-secondary" onclick="clearLogs()">清空</button>
                <button class="btn" onclick="toggleScroll()" id="scrollBtn">暂停滚动</button>
            </div>
        </div>
        <div class="log-content" id="logContent">
            {% for line in logs %}<div class="log-line">{{line}}</div>
            {% else %}<div class="empty-log">暂无日志</div>{% endfor %}
        </div>
        <div class="status-bar">
            <div class="status-indicator">
                <span class="status-dot" id="statusDot"></span>
                <span id="statusText">空闲</span>
            </div>
            <span id="logCount">{{logs|length}} 条日志</span>
        </div>
    </div>
</div>
<script>
var autoScroll=true;
var logContent=document.getElementById('logContent');
function scrollBot(){if(autoScroll)logContent.scrollTop=logContent.scrollHeight;}
function toggleScroll(){autoScroll=!autoScroll;document.getElementById('scrollBtn').textContent=autoScroll?'暂停滚动':'继续滚动';}
function clearLogs(){logContent.innerHTML='<div class=empty-log>日志已清空</div>';document.getElementById('logCount').textContent='0 条日志';}
function esc(t){var d=document.createElement('div');d.textContent=t;return d.innerHTML;}
async function fetchLogs(){
    try{
        var r=await fetch('/api/logs');
        var d=await r.json();
        var dot=document.getElementById('statusDot');
        var txt=document.getElementById('statusText');
        if(d.running){dot.classList.add('running');txt.textContent='运行中';}
        else{dot.classList.remove('running');txt.textContent='空闲';}
        if(d.logs&&d.logs.length>0){
            var html=d.logs.map(function(l){return'<div class=log-line>'+esc(l)+'</div>'}).join('');
            logContent.innerHTML=html;
            document.getElementById('logCount').textContent=d.logs.length+' 条日志';
            scrollBot();
        }
    }catch(e){console.error('获取日志失败:',e);}
}
scrollBot();
setInterval(fetchLogs,2000);
</script>
</body>
</html>"""

# Jinja2 过滤器
def _urlencode(s):
    from urllib.parse import quote
    return quote(str(s), safe='')

_jinja_env = None

def _get_env():
    global _jinja_env
    if _jinja_env is None:
        from jinja2 import Environment, BaseLoader
        _jinja_env = Environment(loader=BaseLoader())
        _jinja_env.filters['encode'] = _urlencode
    return _jinja_env

def _render(name, ctx):
    templates = {
        'index.html': INDEX_HTML,
        'videos.html': VIDEOS_HTML,
        'files.html': FILES_HTML,
        'logs.html': LOGS_HTML,
    }
    tpl = _get_env().from_string(templates[name])
    return tpl.render(**ctx)
