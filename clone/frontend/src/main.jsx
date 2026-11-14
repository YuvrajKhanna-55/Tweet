import { Component, StrictMode, useEffect, useState } from 'react'
import { createRoot } from 'react-dom/client'
import { api } from './api'
import './styles.css'

function Avatar({ user }) {
  return <div className="avatar">{user?.avatar ? <img src={user.avatar} alt="" /> : (user?.display_name || user?.username || '?')[0].toUpperCase()}</div>
}

function Auth({ onAuthenticated, onClose }) {
  const [registering, setRegistering] = useState(false)
  const [form, setForm] = useState({ username: '', email: '', password: '' })
  const [error, setError] = useState('')

  async function submit(event) {
    event.preventDefault()
    setError('')
    try {
      const authenticatedUser = await api(registering ? '/auth/register/' : '/auth/login/', {
        method: 'POST',
        body: JSON.stringify(form),
      })
      onAuthenticated(authenticatedUser)
    } catch (requestError) {
      setError(requestError.message)
    }
  }

  return <div className="modal-backdrop" onMouseDown={event => event.target === event.currentTarget && onClose()}>
    <section className="auth-card modal-card">
      <button className="close-button" onClick={onClose} aria-label="Close">×</button>
      <h1>Tweet</h1>
      <p className="muted">{registering ? 'Create your account' : 'Log in to continue'}</p>
      <form onSubmit={submit}>
        <input placeholder="Username" value={form.username} onChange={event => setForm({ ...form, username: event.target.value })} required />
        {registering && <input type="email" placeholder="Email" value={form.email} onChange={event => setForm({ ...form, email: event.target.value })} required />}
        <input type="password" placeholder="Password" value={form.password} onChange={event => setForm({ ...form, password: event.target.value })} required />
        {error && <p className="error">{error}</p>}
        <button className="primary full">{registering ? 'Create account' : 'Log in'}</button>
      </form>
      <button className="link-button" onClick={() => setRegistering(!registering)}>
        {registering ? 'Already have an account? Log in' : 'Need an account? Register'}
      </button>
    </section>
  </div>
}

function TweetCard({ tweet, user, refresh, requireAuth, onError, onQuote }) {
  async function toggle(action, active) {
    if (!user) {
      requireAuth()
      return
    }
    try {
      await api(`/tweets/${tweet.id}/${action}/`, { method: active ? 'DELETE' : 'POST' })
      refresh()
    } catch (requestError) {
      onError(requestError.message)
    }
  }

  async function reply() {
    if (!user) {
      requireAuth()
      return
    }
    const text = window.prompt('Write a reply')
    if (!text?.trim()) return
    try {
      await api(`/tweets/${tweet.id}/reply/`, { method: 'POST', body: JSON.stringify({ text }) })
      refresh()
    } catch (requestError) {
      onError(requestError.message)
    }
  }

  async function quote() {
    if (!user) {
      requireAuth()
      return
    }
    const text = window.prompt('Add commentary to your quote')
    if (text?.trim()) await onQuote(tweet.id, text)
  }

  async function editTweet() {
    const text = window.prompt('Edit your post', tweet.text)
    if (!text?.trim() || text === tweet.text) return
    try {
      await api(`/tweets/${tweet.id}/`, { method: 'PATCH', body: JSON.stringify({ text }) })
      refresh()
    } catch (requestError) {
      onError(requestError.message)
    }
  }

  async function deleteTweet() {
    if (!window.confirm('Delete this post?')) return
    try {
      await api(`/tweets/${tweet.id}/`, { method: 'DELETE' })
      refresh()
    } catch (requestError) {
      onError(requestError.message)
    }
  }

  return <article className="tweet-card">
    <Avatar user={tweet.user} />
    <div className="tweet-body">
      <div className="tweet-meta"><strong onClick={event => { event.stopPropagation(); window.dispatchEvent(new CustomEvent('tweet:profile', { detail: tweet.user.username })) }}>{tweet.user.display_name}</strong> <span>@{tweet.user.username} · {new Date(tweet.created_at).toLocaleString()}</span></div>
      <p>{tweet.text}</p>
      {tweet.quote_of && <div className="quoted-tweet">Quoted post #{tweet.quote_of}</div>}
      {tweet.photo && <img className="tweet-photo" src={tweet.photo} alt="Tweet attachment" />}
      {tweet.media && /\.(mp4|webm|mov)$/i.test(tweet.media) && <video className="tweet-photo" src={tweet.media} controls />}
      {tweet.media && !/\.(mp4|webm|mov)$/i.test(tweet.media) && <img className="tweet-photo" src={tweet.media} alt="Tweet attachment" />}
      {user?.username === tweet.user.username && <div className="tweet-owner-actions"><button onClick={editTweet}>Edit</button><button onClick={deleteTweet}>Delete</button></div>}
      <div className="tweet-actions">
        <button onClick={reply} aria-label="Reply">💬 {tweet.reply_count}</button>
        <button className={tweet.liked ? 'active' : ''} onClick={() => toggle('like', tweet.liked)} aria-label="Like">♥ {tweet.like_count}</button>
        <button className={tweet.reposted ? 'active' : ''} onClick={() => toggle('repost', tweet.reposted)} aria-label="Repost">↻ {tweet.repost_count}</button>
        <button onClick={quote} aria-label="Quote post">❝</button>
        <button className={tweet.bookmarked ? 'active' : ''} onClick={() => toggle('bookmark', tweet.bookmarked)} aria-label="Bookmark">🔖 {tweet.bookmark_count}</button>
      </div>
    </div>
  </article>
}

function ProfilePanel({ username, user, requireAuth, onError }) {
  const [profile, setProfile] = useState(null)
  const [loading, setLoading] = useState(true)
  const [editing, setEditing] = useState(false)
  const [form, setForm] = useState({ display_name: '', bio: '', location: '', website: '' })
  const [avatar, setAvatar] = useState(null)

  async function loadProfile() {
    setLoading(true)
    try {
      const loaded = await api(`/profiles/${encodeURIComponent(username)}/`)
      setProfile(loaded)
      setForm({
        display_name: loaded.display_name || '',
        bio: loaded.bio || '',
        location: loaded.location || '',
        website: loaded.website || '',
      })
    } catch (requestError) {
      onError(requestError.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { loadProfile() }, [username])

  async function toggleFollow() {
    if (!user) {
      requireAuth()
      return
    }
    try {
      await api(`/profiles/${encodeURIComponent(username)}/follow/`, { method: profile.is_following ? 'DELETE' : 'POST' })
      loadProfile()
    } catch (requestError) {
      onError(requestError.message)
    }
  }

  async function saveProfile(event) {
    event.preventDefault()
    try {
      const body = new FormData()
      Object.entries(form).forEach(([key, value]) => body.append(key, value))
      if (avatar) body.append('avatar', avatar)
      const updated = await api(`/profiles/${encodeURIComponent(username)}/edit/`, { method: 'PATCH', body })
      setProfile(updated)
      setEditing(false)
    } catch (requestError) {
      onError(requestError.message)
    }
  }

  if (loading) return <section className="profile-panel"><p className="muted">Loading profile...</p></section>
  if (!profile) return null
  const isOwner = user?.username === username
  return <section className="profile-panel">
    <div className="profile-cover" />
    <div className="profile-content">
      <Avatar user={profile.user} />
      <div className="profile-heading"><h2>{profile.display_name || profile.user.username}</h2><span>@{profile.user.username}</span></div>
      {isOwner ? <button className="primary" onClick={() => setEditing(!editing)}>{editing ? 'Cancel' : 'Edit profile'}</button> : <button className="primary" onClick={toggleFollow}>{profile.is_following ? 'Following' : 'Follow'}</button>}
      {editing ? <form className="profile-edit-form" onSubmit={saveProfile}>
        <label className="profile-avatar-upload">Profile photo <input type="file" accept="image/*" onChange={event => setAvatar(event.target.files[0] || null)} /></label>
        <input value={form.display_name} placeholder="Display name" onChange={event => setForm({ ...form, display_name: event.target.value })} />
        <textarea value={form.bio} maxLength="160" placeholder="Bio" onChange={event => setForm({ ...form, bio: event.target.value })} />
        <input value={form.location} placeholder="Location" onChange={event => setForm({ ...form, location: event.target.value })} />
        <input value={form.website} type="url" placeholder="Website" onChange={event => setForm({ ...form, website: event.target.value })} />
        <button className="primary">Save profile</button>
      </form> : <>
        <p>{profile.bio || 'No bio yet.'}</p>
        <p className="muted">{profile.location} {profile.website && ` · ${profile.website}`}</p>
      </>}
      <div className="profile-stats"><strong>{profile.following_count} <span>Following</span></strong><strong>{profile.followers_count} <span>Followers</span></strong></div>
    </div>
  </section>
}

function MessagesPanel({ user, onError }) {
  const [conversations, setConversations] = useState([])
  const [selected, setSelected] = useState(null)
  const [message, setMessage] = useState('')
  const [messagePhoto, setMessagePhoto] = useState(null)
  const [username, setUsername] = useState('')
  const [people, setPeople] = useState([])

  async function load() {
    try {
      const data = await api('/conversations/')
      setConversations(data.results || data)
    } catch (requestError) {
      onError(requestError.message)
    }
  }

  useEffect(() => { load() }, [])

  useEffect(() => {
    if (!username.trim()) {
      setPeople([])
      return
    }
    const timer = setTimeout(async () => {
      try {
        setPeople(await api(`/users/?search=${encodeURIComponent(username)}`))
      } catch (requestError) {
        onError(requestError.message)
      }
    }, 250)
    return () => clearTimeout(timer)
  }, [username])

  async function startConversation(event) {
    event.preventDefault()
    if (!username.trim()) return
    try {
      const conversation = await api('/conversations/', {
        method: 'POST',
        body: JSON.stringify({ usernames: [username.trim()] }),
      })
      setSelected(conversation)
      setUsername('')
      load()
    } catch (requestError) {
      onError(requestError.message)
    }
  }

  async function sendMessage(event) {
    event.preventDefault()
    if ((!message.trim() && !messagePhoto) || !selected) return
    try {
      const body = new FormData()
      body.append('text', message)
      if (messagePhoto) body.append('attachment', messagePhoto)
      await api(`/conversations/${selected.id}/messages/`, { method: 'POST', body })
      setMessage('')
      setMessagePhoto(null)
      const history = await api(`/conversations/${selected.id}/history/`)
      setSelected({ ...selected, history })
    } catch (requestError) {
      onError(requestError.message)
    }
  }

  return <section className="messages-panel">
    <form className="new-message" onSubmit={startConversation}>
      <div className="people-search"><input placeholder="Search people to message..." value={username} onChange={event => setUsername(event.target.value)} />{people.length > 0 && <div className="people-results">{people.filter(person => person.username !== user.username).map(person => <button type="button" key={person.id} onClick={() => { setUsername(person.username); setPeople([]) }}><Avatar user={person} /> @{person.username}</button>)}</div>}</div>
      <button className="primary">Open chat</button>
    </form>
    <div className="conversation-list">{conversations.map(conversation => <button key={conversation.id} onClick={async () => setSelected({ ...conversation, history: await api(`/conversations/${conversation.id}/history/`) })}>{conversation.name || conversation.participants.filter(participant => participant.username !== user.username).map(participant => `@${participant.username}`).join(', ')}</button>)}</div>
    {selected && <div className="chat">
      <div className="chat-history">{(selected.history || []).map(item => <p key={item.id}><strong>@{item.sender.username}</strong> {item.text} <button className="reaction-button" onClick={async () => { await api(`/conversations/${selected.id}/react/`, { method: 'POST', body: JSON.stringify({ message_id: item.id, emoji: '👍' }) }) }}>👍</button>{item.photo && <img className="message-photo" src={item.photo} alt="Message attachment" />}{item.attachment && /\.(mp4|webm|mov)$/i.test(item.attachment) && <video className="message-photo" src={item.attachment} controls />}{item.attachment && !/\.(mp4|webm|mov)$/i.test(item.attachment) && <img className="message-photo" src={item.attachment} alt="Message attachment" />}</p>)}</div>
      <form onSubmit={sendMessage}><input value={message} onChange={event => setMessage(event.target.value)} placeholder="Write a message..." /><label className="media-button">📎<input type="file" accept="image/*,.gif,video/mp4,video/webm,video/quicktime" onChange={event => setMessagePhoto(event.target.files[0] || null)} /></label><button className="primary">Send</button></form>
    </div>}
  </section>
}

function CommunitiesPanel({ user, requireAuth, onError }) {
  const [communities, setCommunities] = useState([])
  const [form, setForm] = useState({ name: '', description: '' })
  const [search, setSearch] = useState('')
  const [showCreate, setShowCreate] = useState(false)

  async function load() {
    try {
      const data = await api(`/communities/${search ? `?search=${encodeURIComponent(search)}` : ''}`)
      setCommunities(data.results || data)
    } catch (requestError) {
      onError(requestError.message)
    }
  }

  useEffect(() => { load() }, [search])

  async function createCommunity(event) {
    event.preventDefault()
    if (!user) {
      requireAuth()
      return
    }
    try {
      await api('/communities/', { method: 'POST', body: JSON.stringify(form) })
      setForm({ name: '', description: '' })
      load()
    } catch (requestError) {
      onError(requestError.message)
    }
  }

  async function toggleMembership(community) {
    if (!user) {
      requireAuth()
      return
    }
    try {
      await api(`/communities/${community.id}/membership/`, { method: community.is_member ? 'DELETE' : 'POST' })
      load()
    } catch (requestError) {
      onError(requestError.message)
    }
  }

  return <section className="communities-panel">
    <div className="community-toolbar"><input placeholder="Search communities..." value={search} onChange={event => setSearch(event.target.value)} /><button className="primary" onClick={() => user ? setShowCreate(!showCreate) : requireAuth()}>＋ Create community</button></div>
    {showCreate && <form className="community-create" onSubmit={createCommunity}>
      <input placeholder="Community name" value={form.name} onChange={event => setForm({ ...form, name: event.target.value })} required />
      <input placeholder="Description" value={form.description} onChange={event => setForm({ ...form, description: event.target.value })} />
      <button className="primary">Create</button>
    </form>}
    {communities.map(community => <article className="community-card" key={community.id}><div><h3>{community.name}</h3><p className="muted">{community.description || 'No description yet.'}</p><small>{community.members_count} members</small></div><button className="secondary" onClick={() => toggleMembership(community)}>{community.is_member ? 'Joined' : 'Join'}</button></article>)}
  </section>
}

function PostDetailPanel({ tweetId, user, requireAuth, onError, onQuote }) {
  const [tweet, setTweet] = useState(null)
  const [replies, setReplies] = useState([])
  const [replyText, setReplyText] = useState('')

  async function load() {
    try {
      const [post, postReplies] = await Promise.all([
        api(`/tweets/${tweetId}/`),
        api(`/tweets/${tweetId}/replies/`),
      ])
      setTweet(post)
      setReplies(postReplies)
    } catch (requestError) {
      onError(requestError.message)
    }
  }

  useEffect(() => { load() }, [tweetId])

  async function reply(event) {
    event.preventDefault()
    if (!user) {
      requireAuth()
      return
    }
    if (!replyText.trim()) return
    try {
      await api(`/tweets/${tweetId}/reply/`, { method: 'POST', body: JSON.stringify({ text: replyText }) })
      setReplyText('')
      load()
    } catch (requestError) {
      onError(requestError.message)
    }
  }

  if (!tweet) return <p className="muted empty">Loading post...</p>
  return <section className="post-detail">
    <TweetCard tweet={tweet} user={user} refresh={load} requireAuth={requireAuth} onError={onError} onQuote={onQuote} />
    <form className="detail-reply" onSubmit={reply}>
      <Avatar user={user} />
      <input value={replyText} onChange={event => setReplyText(event.target.value)} placeholder={user ? 'Post your reply' : 'Log in to reply'} />
      <button className="primary">Reply</button>
    </form>
    <h3 className="replies-heading">Replies</h3>
    {replies.map(replyTweet => <TweetCard key={replyTweet.id} tweet={replyTweet} user={user} refresh={load} requireAuth={requireAuth} onError={onError} onQuote={onQuote} />)}
    {!replies.length && <p className="muted empty">No replies yet.</p>}
  </section>
}

function App({ user, setUser, startupError }) {
  const [tweets, setTweets] = useState([])
  const [text, setText] = useState('')
  const [search, setSearch] = useState('')
  const [tab, setTab] = useState('feed')
  const [profileUsername, setProfileUsername] = useState(null)
  const [selectedTweetId, setSelectedTweetId] = useState(null)
  const [notifications, setNotifications] = useState([])
  const [authOpen, setAuthOpen] = useState(false)
  const [error, setError] = useState(startupError)
  const [photo, setPhoto] = useState(null)

  function requireAuth() {
    setAuthOpen(true)
  }

  async function loadTweets(path) {
    try {
      const data = await api(`${path}${search ? `?search=${encodeURIComponent(search)}` : ''}`)
      setTweets(data.results || data)
      setError('')
    } catch (requestError) {
      setError(requestError.message)
    }
  }

  function feedPath() {
    if (tab === 'bookmarks') return '/tweets/bookmarks/'
    if (tab === 'following') return '/tweets/following/'
    return '/tweets/'
  }

  useEffect(() => { loadTweets(feedPath()) }, [tab, user])
  useEffect(() => {
    const handleProfile = event => viewProfile(event.detail)
    window.addEventListener('tweet:profile', handleProfile)
    return () => window.removeEventListener('tweet:profile', handleProfile)
  }, [])

  async function publish(event) {
    event.preventDefault()
    if (!user) {
      requireAuth()
      return
    }
    if (!text.trim()) return
    try {
      const body = new FormData()
      body.append('text', text)
      if (photo) body.append('media', photo)
      await api('/tweets/', { method: 'POST', body })
      setText('')
      setPhoto(null)
      loadTweets(feedPath())
    } catch (requestError) {
      setError(requestError.message)
    }

  }

  async function quoteTweet(tweetId, quoteText) {
    try {
      await api(`/tweets/${tweetId}/quote/`, {
        method: 'POST',
        body: JSON.stringify({ text: quoteText }),
      })
      loadTweets(feedPath())
    } catch (requestError) {
      setError(requestError.message)
    }
  }

  async function openNotifications() {
    if (!user) {
      requireAuth()
      return
    }
    try {
      setNotifications(await api('/notifications/'))
    } catch (requestError) {
      setError(requestError.message)
    }
  }

  async function logout() {
    await api('/auth/logout/', { method: 'POST' })
    setUser(null)
    setTab('feed')
  }

  function viewProfile(username) {
    setProfileUsername(username)
    setTab('profile')
  }

  function viewPost(tweetId) {
    setSelectedTweetId(tweetId)
    setTab('post')
  }

  return <div className="app-shell">
    <aside className="sidebar">
      <h1 className="logo"><span className="brand-bird" aria-hidden="true">🐦</span> Tweet</h1>
      <nav>
        <button className={tab === 'feed' ? 'selected' : ''} onClick={() => { setTab('feed'); setProfileUsername(null) }}>⌂ For You</button>
        <button className={tab === 'following' ? 'selected' : ''} onClick={() => user ? setTab('following') : requireAuth()}>✦ Following</button>
        <button className={tab === 'bookmarks' ? 'selected' : ''} onClick={() => user ? setTab('bookmarks') : requireAuth()}>🔖 Bookmarks</button>
        <button className={tab === 'notifications' ? 'selected' : ''} onClick={() => { setTab('notifications'); openNotifications() }}>🔔 Notifications</button>
        <button className={tab === 'communities' ? 'selected' : ''} onClick={() => setTab('communities')}>◉ Communities</button>
        <button className={tab === 'messages' ? 'selected' : ''} onClick={() => user ? setTab('messages') : requireAuth()}>✉ Messages</button>
        <button className={tab === 'profile' ? 'selected' : ''} onClick={() => user ? viewProfile(user.username) : requireAuth()}>👤 {user ? `@${user.username}` : 'Profile'}</button>
      </nav>
      {user ? <button className="secondary full" onClick={logout}>Log out</button> : <button className="primary full" onClick={requireAuth}>Log in</button>}
    </aside>
    <main className="feed">
      <header className="feed-header">
        <h2>{tab === 'bookmarks' ? 'Bookmarks' : tab === 'following' ? 'Following' : tab === 'profile' ? `@${profileUsername}` : tab === 'post' ? 'Post' : tab === 'notifications' ? 'Notifications' : tab === 'messages' ? 'Messages' : tab === 'communities' ? 'Communities' : 'For You'}</h2>
        {tab !== 'profile' && tab !== 'notifications' && tab !== 'messages' && tab !== 'communities' && <input placeholder="Search tweets..." value={search} onChange={event => setSearch(event.target.value)} onKeyDown={event => event.key === 'Enter' && loadTweets(feedPath())} />}
      </header>
      {error && <p className="error global-error">{error}</p>}
      {tab === 'profile' && profileUsername && <ProfilePanel username={profileUsername} user={user} requireAuth={requireAuth} onError={setError} />}
      {tab === 'post' && selectedTweetId && <PostDetailPanel tweetId={selectedTweetId} user={user} requireAuth={requireAuth} onError={setError} onQuote={quoteTweet} />}
      {tab === 'notifications' && <section className="notifications">{notifications.length ? notifications.map(notification => <p key={notification.id}><strong>@{notification.actor.username}</strong> {notification.kind} your post.</p>) : <p className="muted empty">No notifications yet.</p>}</section>}
      {tab === 'messages' && <MessagesPanel user={user} onError={setError} />}
      {tab === 'communities' && <CommunitiesPanel user={user} requireAuth={requireAuth} onError={setError} />}
      {tab !== 'profile' && tab !== 'post' && tab !== 'notifications' && tab !== 'messages' && tab !== 'communities' && <>
        <form className="composer" onSubmit={publish}>
          <Avatar user={user} />
          <div className="composer-content"><textarea value={text} onChange={event => setText(event.target.value)} maxLength="280" placeholder={user ? 'What is happening?!' : 'Log in to post'} /><div className="composer-footer"><label className="media-button">📎 <input type="file" accept="image/*,.gif,video/mp4,video/webm,video/quicktime" onChange={event => setPhoto(event.target.files[0] || null)} /></label><span>{photo?.name || `${text.length}/280`}</span><button className="primary">Post</button></div></div>
        </form>
        {error && <p className="error">{error}</p>}
        {tweets.map(tweet => <div key={tweet.id} onClick={event => event.target.tagName !== 'BUTTON' && viewPost(tweet.id)}><TweetCard tweet={tweet} user={user} refresh={() => loadTweets(feedPath())} requireAuth={requireAuth} onError={setError} onQuote={quoteTweet} /></div>)}
        {!tweets.length && <p className="muted empty">No tweets to show yet. Be the first to post!</p>}
      </>}
    </main>
    <aside className="right-panel">
      <h3><span className="brand-bird small" aria-hidden="true">🐦</span> What's happening</h3>
      <p className="muted">Anyone can read the public feed. Log in to post, follow, like, reply, repost, bookmark, or edit your content.</p>
    </aside>
    {authOpen && <Auth onAuthenticated={authenticatedUser => { setUser(authenticatedUser); setAuthOpen(false) }} onClose={() => setAuthOpen(false)} />}
  </div>
}

function Root() {
  const [user, setUser] = useState(undefined)
  const [startupError, setStartupError] = useState('')
  useEffect(() => {
    api('/auth/me/')
      .then(data => setUser(data.user === null ? null : data))
      .catch(() => {
        setUser(null)
        setStartupError('Django is not reachable. Start the backend with: python manage.py runserver')
      })
  }, [])
  if (user === undefined) return <div className="loading">Loading...</div>
  return <App user={user} setUser={setUser} startupError={startupError} />
}

class AppErrorBoundary extends Component {
  state = { hasError: false }

  static getDerivedStateFromError() {
    return { hasError: true }
  }

  render() {
    if (this.state.hasError) {
      return <main className="error-page">
        <h1>Tweet could not load</h1>
        <p>Refresh the page to try again.</p>
        <button className="primary" onClick={() => window.location.reload()}>Refresh</button>
      </main>
    }
    return this.props.children
  }
}

const rootElement = document.getElementById('root')
const reactRoot = globalThis.__tweetReactRoot || createRoot(rootElement)
globalThis.__tweetReactRoot = reactRoot
reactRoot.render(<StrictMode><AppErrorBoundary><Root /></AppErrorBoundary></StrictMode>)
