defmodule Sc2Web.GameChannel do
  @moduledoc """
  Phoenix Channel for real-time SC2 game updates.
  Handles live game events, spectator presence, and broadcasts.
  """
  use Sc2Web, :channel
  alias Sc2Web.Presence
  alias Sc2.GameServer

  @impl true
  def join("game:" <> game_id, payload, socket) do
    if authorized?(payload) do
      send(self(), {:after_join, game_id})
      socket =
        socket
        |> assign(:game_id, game_id)
        |> assign(:role, payload["role"] || "spectator")
      {:ok, %{status: "joined", game_id: game_id}, socket}
    else
      {:error, %{reason: "unauthorized"}}
    end
  end

  @impl true
  def handle_info({:after_join, game_id}, socket) do
    {:ok, _} =
      Presence.track(socket, socket.assigns.user_id, %{
        online_at: inspect(System.system_time(:second)),
        role: socket.assigns.role,
        game_id: game_id
      })
    push(socket, "presence_state", Presence.list(socket))
    {:noreply, socket}
  end

  # Client sends unit kill event
  @impl true
  def handle_in("unit_killed", %{"unit_type" => unit, "player" => player} = payload, socket) do
    game_id = socket.assigns.game_id
    GameServer.record_kill(game_id, unit, player)
    broadcast!(socket, "unit_killed", %{
      unit_type: unit,
      player: player,
      timestamp: System.system_time(:millisecond)
    })
    {:noreply, socket}
  end

  # Resource update from game engine
  def handle_in("resource_update", %{"minerals" => min, "vespene" => gas, "supply" => supply}, socket) do
    game_id = socket.assigns.game_id
    GameServer.update_resources(game_id, %{minerals: min, vespene: gas, supply: supply})
    broadcast!(socket, "resource_update", %{
      minerals: min,
      vespene: gas,
      supply: supply,
      game_id: game_id
    })
    {:noreply, socket}
  end

  # Game ended event
  def handle_in("game_ended", %{"winner" => winner, "duration" => duration}, socket) do
    game_id = socket.assigns.game_id
    GameServer.end_game(game_id, winner, duration)
    broadcast!(socket, "game_ended", %{
      winner: winner,
      duration: duration,
      game_id: game_id,
      ended_at: DateTime.utc_now() |> DateTime.to_iso8601()
    })
    {:stop, :normal, socket}
  end

  # Intercept outgoing broadcasts to filter by role
  @impl true
  def handle_out("unit_killed", payload, socket) do
    push(socket, "unit_killed", payload)
    {:noreply, socket}
  end

  def handle_out("game_ended", payload, socket) do
    push(socket, "game_ended", Map.put(payload, :spectator_count, spectator_count(socket)))
    {:noreply, socket}
  end

  defp authorized?(%{"token" => token}), do: Sc2.Auth.verify_token(token) == :ok
  defp authorized?(_), do: false

  defp spectator_count(socket) do
    socket |> Presence.list() |> map_size()
  end
end
