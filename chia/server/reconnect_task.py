import asyncio
import socket
import dns.asyncresolver

from chia.server.server import ChiaServer
from chia.types.peer_info import PeerInfo
from chia.server.outbound_message import NodeType


def start_reconnect_task(server: ChiaServer, peer_info_arg: PeerInfo, log, auth: bool):
    """
    Start a background task that checks connection and reconnects periodically to a peer.
    """
    peer_info_origin = PeerInfo(socket.gethostbyname(peer_info_arg.host), peer_info_arg.port)
    resolver = dns.asyncresolver.Resolver()

    async def query_dns() -> None:
        peers: List[PeerInfo] = []
        try:
            result = await resolver.resolve(qname=peer_info_arg.host, lifetime=30)
            for ip in result:
                peers.append(
                    PeerInfo(
                        ip.to_text(),
                        peer_info_arg.port,
                    )
                )
            log.info(f"Received {len(peers)} peers from DNS seeder.")
        except Exception as e:
            log.error(f"Exception while querying DNS server: {e}")

        return peers

    async def connection_check(peer_info: PeerInfo):
        while True:
            peer_retry = True
            for _, connection in server.all_connections.items():
                if connection.get_peer_info() == peer_info or connection.get_peer_info() == peer_info_arg:
                    peer_retry = False
            if peer_retry:
                if server._local_type == NodeType.HARVESTER:
                    peers = await query_dns()
                    if len(peers) > 0:
                        peer_info = peers[0]
                log.info(f"Reconnecting to peer {peer_info}")
                try:
                    await server.start_client(peer_info, None, auth=auth)
                except Exception as e:
                    log.info(f"Failed to connect to {peer_info} {e}")
            await asyncio.sleep(3)

    return asyncio.create_task(connection_check(peer_info_origin))
