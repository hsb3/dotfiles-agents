import { Button, Column, Grid, InlineNotification, PasswordInput, TextInput } from "@carbon/react";
import { type FormEvent, type ReactNode, useState } from "react";
import type { Session } from "./api";

export async function submitLogin(session: Pick<Session, "login">, email: string, password: string, clearPassword: (value: string) => void) {
  try { return await session.login(email, password); } finally { clearPassword(""); }
}

export function Block({ children }: { children: ReactNode }) {
  return <Grid fullWidth className="content-block"><Column sm={4} md={8} lg={16}>{children}</Column></Grid>;
}

export function StateNotice({ state, subject }: { state: "loading" | "access" | "error" | "empty"; subject: string }) {
  const copy = {
    loading: [`Loading ${subject}`, "Please wait while Toolbox reads the current records."],
    access: [`${subject[0].toUpperCase() + subject.slice(1)} access expired`, "Sign in again to read private records."],
    error: [`Could not load ${subject}`, "The service did not return a usable response. Try again."],
    empty: [`No ${subject} records`, "This accessible source currently has no records."],
  }[state];
  return <InlineNotification kind={state === "error" ? "error" : "info"} lowContrast hideCloseButton title={copy[0]} subtitle={copy[1]} />;
}

export function Login({ session, onAuthenticated }: { session: Session; onAuthenticated: () => void }) {
  const [email, setEmail] = useState(""); const [password, setPassword] = useState(""); const [message, setMessage] = useState("");
  async function onSubmit(event: FormEvent) {
    event.preventDefault();
    const result = await submitLogin(session, email, password, setPassword);
    if (result.kind === "ok") onAuthenticated(); else setMessage(result.kind === "access" ? "Sign-in details were not accepted." : result.message || "Could not sign in.");
  }
  return <main className="login-main" aria-labelledby="login-title"><Grid fullWidth><Column sm={4} md={6} lg={6}><section className="login-card"><p className="eyebrow">Toolbox</p><h1 id="login-title">Sign in to your workspace</h1><p>Use your ordinary Toolbox account to read the records available to you.</p>{message && <InlineNotification kind="error" lowContrast hideCloseButton title="Sign-in failed" subtitle={message} />}
    <form onSubmit={onSubmit}><TextInput id="email" labelText="Email" type="email" value={email} onChange={(event) => setEmail(event.currentTarget.value)} required /><PasswordInput id="password" labelText="Password" value={password} onChange={(event) => setPassword(event.currentTarget.value)} required /><Button type="submit">Sign in</Button></form>
  </section></Column></Grid></main>;
}
