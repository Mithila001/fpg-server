import { useEffect, useState } from "react";
import client from "../api/client";

type User = { id: number; name: string; email: string };

export default function UserList() {
  const [users, setUsers] = useState<User[]>([]);

  useEffect(() => {
    client.get("/users/").then((res) => setUsers(res.data));
  }, []);

  return (
    <ul>
      {users.map((u) => (
        <li key={u.id}>
          {u.name} - {u.email}
        </li>
      ))}
    </ul>
  );
}
