// Verify exact lower and upper bounds for 4x4 Classic Dark Hex.

#include <algorithm>
#include <array>
#include <bit>
#include <cstddef>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <limits>
#include <memory>
#include <span>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <utility>
#include <vector>

using History = unsigned __int128;
using Mask = std::uint16_t;
using Id = std::uint32_t;
using Mass = unsigned __int128;
using Worlds = std::vector<Id>;
constexpr int Rows = 4;
constexpr int Columns = 4;
constexpr int Cells = Rows * Columns;
constexpr int Players = 2;
constexpr int Black = 0;
constexpr int HistoryEventBits = 6;
constexpr unsigned HistoryEventMask = (1U << HistoryEventBits) - 1;
constexpr Mask All = (1U << Cells) - 1;
constexpr Mask BlackStart = 0x000f;
constexpr Mask BlackGoal = 0xf000;
constexpr Mask WhiteStart = 0x1111;
constexpr Mask WhiteGoal = 0x8888;
constexpr std::array<int, Cells> ProbeOrder = {
    5, 6, 9, 10, 1, 2, 4, 7, 8, 11, 13, 14, 0, 3, 12, 15
};

Mask bit(int cell) {
    return Mask(1U << cell);
}

void require(bool condition, const char* message) {
    if (!condition) {
        throw std::runtime_error(message);
    }
}

Mass add(Mass a, Mass b) {
    require(b <= std::numeric_limits<Mass>::max() - a, "mass overflow");
    return a + b;
}

std::uint64_t mix(std::uint64_t x) {
    x ^= x >> 30;
    x *= 0xbf58476d1ce4e5b9ULL;
    x ^= x >> 27;
    x *= 0x94d049bb133111ebULL;
    return x ^ (x >> 31);
}

struct HistoryHash {
    std::size_t operator()(History h) const {
        return mix(std::uint64_t(h) ^ mix(std::uint64_t(h >> 64)));
    }
};

History append(History h, int cell, bool success) {
    require(!(h >> (HistoryEventBits * (Cells - 1))), "private history exceeds board");
    return (h << HistoryEventBits) | ((cell + 1) << 1) | success;
}

History rotate(History h) {
    History result = 0;
    for (int shift = 0; h; shift += HistoryEventBits, h >>= HistoryEventBits) {
        unsigned event = unsigned(h & HistoryEventMask);
        result |= History(((Cells + 1 - (event >> 1)) << 1) | (event & 1)) << shift;
    }
    return result;
}

struct Board {
    std::array<Mask, Cells> adjacent{};
    std::array<std::array<bool, std::size_t(All) + 1>, Players> won{};

    Board() {
        constexpr int dr[] = {-1, -1, 0, 0, 1, 1};
        constexpr int dc[] = {0, 1, -1, 1, -1, 0};
        for (int cell = 0; cell < Cells; ++cell) {
            for (int direction = 0; direction < 6; ++direction) {
                int row = cell / Columns + dr[direction];
                int column = cell % Columns + dc[direction];
                if (row >= 0 && row < Rows && column >= 0 && column < Columns) {
                    adjacent[cell] |= bit(Columns * row + column);
                }
            }
        }
        for (int player = 0; player < Players; ++player) {
            for (unsigned stones = 0; stones <= All; ++stones) {
                Mask reached = Mask(stones & (player == Black ? BlackStart : WhiteStart));
                Mask pending = reached;
                while (pending) {
                    int cell = std::countr_zero(pending);
                    pending &= pending - 1;
                    Mask fresh = adjacent[cell] & stones & ~reached;
                    reached |= fresh;
                    pending |= fresh;
                }
                won[player][stones] = bool(
                    reached & (player == Black ? BlackGoal : WhiteGoal));
            }
        }
    }
};

struct Action {
    int cell;
    Mass mass;
    std::array<Id, 2> next{};
};

struct Node {
    History history = 0;
    Mask own = 0;
    Mask seen = 0;
    Mass mass = 0;
    std::vector<Action> actions;
};

struct Graph {
    int owner;
    Mass total;
    bool symmetric = true;
    std::vector<Node> nodes;
    std::unordered_map<History, Id, HistoryHash> ids;

    explicit Graph(const std::string& path) {
        std::ifstream in(path);
        require(bool(in), "cannot open certificate");

        auto integer = [&]() {
            std::string token;
            in >> token;
            require(!token.empty(), "missing integer");
            Mass value = 0;
            for (char c : token) {
                require(c >= '0' && c <= '9', "invalid integer");
                require(value <= (std::numeric_limits<Mass>::max() - (c - '0')) / 10,
                        "integer overflow");
                value = value * 10 + (c - '0');
            }
            return value;
        };
        int rows, columns, opening;
        Id root;
        in >> rows >> columns >> opening >> owner >> root;
        require(rows == Rows && columns == Columns, "board is not 4x4");
        total = integer();
        std::size_t count;
        int orientations;
        in >> count >> orientations;
        std::array<std::array<int, Cells>, 2> cells;
        for (auto& permutation : cells) {
            for (int& cell : permutation) {
                in >> cell;
            }
        }
        struct Edge {
            int cell;
            Id failure;
            Id success;
            Mass weight;
        };
        std::vector<std::vector<Edge>> profiles(count);
        for (auto& profile : profiles) {
            std::size_t actions;
            in >> actions;
            for (std::size_t i = 0; i < actions; ++i) {
                Edge edge;
                in >> edge.cell >> edge.failure >> edge.success;
                edge.weight = integer();
                profile.push_back(edge);
            }
        }

        // A reference is twice the profile number plus its rotation bit.
        // Only cell labels rotate; success and collision retain their meaning.
        auto expand = [&](auto&& self, Id reference, History history,
                          Mask own, Mask seen, Mass incoming) -> Id {
            Id id = Id(nodes.size());
            ids.emplace(history, id);
            nodes.push_back(Node{history, own, seen, incoming, {}});
            const auto& profile = profiles[reference / 2];
            int orientation = reference % 2;
            if (profile.empty()) {
                return id;
            }
            Mass denominator = 0;
            for (const Edge& edge : profile) {
                denominator = add(denominator, edge.weight);
            }
            // Coprime local weights make their sum divide the incoming mass.
            // Divide first so the intermediate product stays within TOTAL.
            require(incoming % denominator == 0, "nonintegral action mass");
            Mass unit = incoming / denominator;
            Mask used = seen;
            for (const Edge& edge : profile) {
                int cell = cells[orientation][edge.cell];
                require(!(used & bit(cell)), "action repeats a probe");
                used |= bit(cell);
                Mass mass = unit * edge.weight;
                auto child = [&](Id next, bool success) {
                    Id rotated = (next & ~Id(1)) | ((next & 1) ^ orientation);
                    return self(self, rotated, append(history, cell, success),
                                Mask(own | (success ? bit(cell) : 0)),
                                Mask(seen | bit(cell)), mass);
                };
                Id failure = child(edge.failure, false);
                Id success = child(edge.success, true);
                nodes[id].actions.push_back(Action{cell, mass, {failure, success}});
            }
            return id;
        };
        expand(expand, root, 0, 0, 0, total);
        for (const Node& node : nodes) {
            if (!node.actions.empty()) {
                auto other = ids.find(rotate(node.history));
                if (other == ids.end()) {
                    symmetric = false;
                    break;
                }
                const auto& rotated = nodes[other->second].actions;
                if (rotated.size() != node.actions.size()) {
                    symmetric = false;
                    break;
                }
                for (const Action& a : node.actions) {
                    if (std::none_of(rotated.begin(), rotated.end(), [&](const Action& b) {
                        return b.cell == Cells - 1 - a.cell && b.mass == a.mass;
                    })) {
                        symmetric = false;
                    }
                }
            }
        }
    }
};

// Chunked storage avoids copying the whole cache when it grows. Hash matches
// are checked against the complete state, including every hidden history.
class Memo {
    struct Entry {
        Mass value;
        Id offset;
        Id hash;
        std::uint16_t size;
        Mask own;
        Mask seen;
        std::uint8_t action;
    };

    static constexpr unsigned Shift = 18;
    static constexpr unsigned Chunk = 1U << Shift;
    static constexpr unsigned Low = Chunk - 1;
    std::vector<std::unique_ptr<Entry[]>> entries;
    std::vector<std::unique_ptr<Id[]>> worlds;
    std::vector<Id> buckets;
    Id used = 0;
    Id world_used = Chunk;

    Entry& entry(Id id) {
        return entries[id >> Shift][id & Low];
    }

    bool equal(const Entry& e, Mask own, Mask seen, std::span<const Id> ids) const {
        if (e.own != own || e.seen != seen || e.size != ids.size()) {
            return false;
        }
        const Id* p = worlds[e.offset >> Shift].get() + (e.offset & Low);
        return std::equal(ids.begin(), ids.end(), p);
    }

    void rehash(std::size_t size) {
        std::vector<Id> replacement(size);
        for (Id i = 0; i < used; ++i) {
            std::size_t slot = entry(i).hash & (size - 1);
            while (replacement[slot]) {
                slot = (slot + 1) & (size - 1);
            }
            replacement[slot] = i + 1;
        }
        buckets.swap(replacement);
    }

public:
    static Id hash(Mask own, Mask seen, std::span<const Id> ids) {
        auto result = mix(std::uint64_t(own) | (std::uint64_t(seen) << Cells));
        for (Id id : ids) {
            result = mix(result ^ id);
        }
        return Id(result ^ (result >> 32));
    }

    bool get(Mask own, Mask seen, std::span<const Id> ids, Id hash,
             Mass& value, int& action) {
        if (buckets.empty()) {
            return false;
        }
        std::size_t slot = hash & (buckets.size() - 1);
        while (buckets[slot]) {
            const Entry& e = entry(buckets[slot] - 1);
            if (e.hash == hash && equal(e, own, seen, ids)) {
                value = e.value;
                action = e.action;
                return true;
            }
            slot = (slot + 1) & (buckets.size() - 1);
        }
        return false;
    }

    void put(Mask own, Mask seen, std::span<const Id> ids, Id hash,
             Mass value, int action) {
        require(ids.size() <= std::numeric_limits<std::uint16_t>::max()
                    && used < 100000000,
                "memo capacity exceeded");
        if (buckets.empty()) {
            rehash(1024);
        }
        if ((std::size_t(used) + 1) * 10 > buckets.size() * 8) {
            rehash(buckets.size() * 2);
        }
        if ((used & Low) == 0) {
            entries.emplace_back(new Entry[Chunk]);
        }
        if (world_used + ids.size() > Chunk) {
            require(worlds.size() < (1U << (32 - Shift)), "world arena capacity exceeded");
            worlds.emplace_back(new Id[Chunk]);
            world_used = 0;
        }
        Id offset = (Id(worlds.size() - 1) << Shift) | world_used;
        std::copy(ids.begin(), ids.end(), worlds.back().get() + world_used);
        world_used += ids.size();
        entry(used) = Entry{
            value, offset, hash, std::uint16_t(ids.size()), own, seen, std::uint8_t(action)
        };
        std::size_t slot = hash & (buckets.size() - 1);
        while (buckets[slot]) {
            slot = (slot + 1) & (buckets.size() - 1);
        }
        buckets[slot] = ++used;
    }
};

class BestResponder {
    const Graph& graph;
    const Board& board;
    int me;
    Memo memo;
    struct Transition {
        std::uint64_t key = ~std::uint64_t(0);
        Worlds worlds;
    };

    std::vector<Transition> transitions = std::vector<Transition>(1U << 18);
    std::unordered_map<History, int, HistoryHash> policy;

    Mass mass(const Worlds& worlds) const {
        Mass result = 0;
        for (Id id : worlds) {
            result = add(result, graph.nodes[id].mass);
        }
        return result;
    }

    static void canonical(Worlds& worlds) {
        std::sort(worlds.begin(), worlds.end());
        require(std::adjacent_find(worlds.begin(), worlds.end()) == worlds.end(),
                "duplicate hidden history");
    }

    Worlds advance(Mask own, Id id) {
        std::uint64_t key = (std::uint64_t(id) << Cells) | own;
        Transition& cached = transitions[mix(key) & (transitions.size() - 1)];
        if (cached.key == key) {
            return cached.worlds;
        }
        const Node& node = graph.nodes[id];
        require(!node.actions.empty(), "missing reachable decision");
        Worlds result;
        for (const Action& action : node.actions) {
            bool success = !(own & bit(action.cell));
            Id child = action.next[success];
            if (!success) {
                auto next = advance(own, child);
                result.insert(result.end(), next.begin(), next.end());
            } else if (!board.won[graph.owner][graph.nodes[child].own]) {
                result.push_back(child);
            }
        }
        canonical(result);
        cached.key = key;
        cached.worlds = result;
        return result;
    }

    Mass expand(Mask own, int action, const Worlds& worlds,
                Worlds& collision, Worlds& success) {
        Mass wins = 0;
        Mask placed = own | bit(action);
        for (Id id : worlds) {
            if (graph.nodes[id].own & bit(action)) {
                collision.push_back(id);
            } else if (board.won[me][placed]) {
                wins = add(wins, graph.nodes[id].mass);
            } else {
                auto next = advance(placed, id);
                success.insert(success.end(), next.begin(), next.end());
            }
        }
        canonical(collision);
        canonical(success);
        return wins;
    }

    Mass value(Mask own, Mask seen, const Worlds& worlds) {
        if (worlds.empty()) {
            return 0;
        }

        // The responder's knowledge and the consistent opponent histories
        // determine every future payoff. Earlier probe order adds nothing
        // once these are fixed.
        Id hash = Memo::hash(own, seen, worlds);
        Mass best;
        int action;
        if (memo.get(own, seen, worlds, hash, best, action)) {
            return best;
        }
        require(++nodes <= 100000000, "node limit exceeded");

        // A certain collision gives no information and costs no turn, so
        // its continuation can be played immediately without the probe.
        Mask certain = All;
        for (Id id : worlds) {
            certain &= graph.nodes[id].own;
        }
        Mask legal = All & ~seen & ~certain;

        // Try a connection-completing probe first. Success wins immediately;
        // failure leaves every other option available without losing a turn.
        for (int cell = 0; cell < Cells; ++cell) {
            if ((legal & bit(cell)) && board.won[me][own | bit(cell)]) {
                legal = bit(cell);
                break;
            }
        }
        Mass total = mass(worlds);
        best = 0;
        action = -1;
        for (int cell : ProbeOrder) {
            // Rotation invariance makes the two halves equivalent at the root.
            if (!(legal & bit(cell)) || (!seen && graph.symmetric && cell >= Cells / 2)) {
                continue;
            }
            Worlds collision;
            Worlds success;
            Mass score = expand(own, cell, worlds, collision, success);
            Mass success_mass = mass(success);
            // An unresolved branch can contribute at most its remaining mass.
            if (action >= 0 && add(add(score, mass(collision)), success_mass) <= best) {
                continue;
            }
            score = add(score, value(own, seen | bit(cell), collision));
            if (action >= 0 && add(score, success_mass) <= best) {
                continue;
            }
            score = add(score, value(own | bit(cell), seen | bit(cell), success));
            if (action < 0 || score > best) {
                best = score;
                action = cell;
            }
            if (best == total) {
                break;
            }
        }
        require(action >= 0 && best <= total, "invalid response value");
        memo.put(own, seen, worlds, hash, best, action);
        return best;
    }

    void extract(History history, Mask own, Mask seen, const Worlds& worlds) {
        if (worlds.empty() || policy.contains(history)) {
            return;
        }
        Mass wins;
        int action;
        require(memo.get(own, seen, worlds, Memo::hash(own, seen, worlds), wins, action),
                "missing response node");
        policy.emplace(history, action);
        Worlds collision;
        Worlds success;
        expand(own, action, worlds, collision, success);
        extract(append(history, action, false), own, seen | bit(action), collision);
        extract(append(history, action, true), own | bit(action), seen | bit(action), success);
    }

    // Replay the fixed response on actual boards without using cached values.
    Mass replay(Mask black, Mask white, Id owner_history,
                History response_history, int turn) const {
        const Node& node = graph.nodes[owner_history];
        if (turn == graph.owner) {
            require(!node.actions.empty(), "missing replay decision");
            Mass result = 0;
            for (const Action& action : node.actions) {
                bool success = !((black | white) & bit(action.cell));
                Mask next_black = black;
                Mask next_white = white;
                if (success) {
                    (turn == Black ? next_black : next_white) |= bit(action.cell);
                }
                Mask stones = turn == Black ? next_black : next_white;
                if (!success || !board.won[turn][stones]) {
                    result = add(result, replay(next_black, next_white, action.next[success],
                                               response_history, success ? me : turn));
                }
            }
            return result;
        }
        auto it = policy.find(response_history);
        require(it != policy.end(), "missing response action");
        int action = it->second;
        bool success = !((black | white) & bit(action));
        if (success) {
            (me == Black ? black : white) |= bit(action);
        }
        if (success && board.won[me][me == Black ? black : white]) {
            return node.mass;
        }
        return replay(black, white, owner_history,
                      append(response_history, action, success), success ? graph.owner : me);
    }

public:
    std::uint64_t nodes = 0;

    BestResponder(const Graph& graph, const Board& board_data)
        : graph(graph), board(board_data), me(1 - graph.owner) {}

    Mass solve() {
        Worlds worlds = graph.owner == Black ? advance(0, 0) : Worlds{0};
        Mass wins = value(0, 0, worlds);
        extract(0, 0, 0, worlds);
        require(replay(0, 0, 0, 0, 0) == wins, "response replay mismatch");
        std::cout << "best_response_nodes " << nodes
                  << "\nresponse_infosets " << policy.size()
                  << "\nreplay ok\n";
        return wins;
    }
};

std::string decimal(Mass value) {
    std::string result;
    do {
        result.push_back(char('0' + value % 10));
        value /= 10;
    } while (value);
    std::reverse(result.begin(), result.end());
    return result;
}

std::string fraction(Mass numerator, Mass denominator) {
    Mass a = numerator, b = denominator;
    while (b) {
        Mass remainder = a % b;
        a = b;
        b = remainder;
    }
    return decimal(numerator / a) + "/" + decimal(denominator / a);
}

int main(int argc, char** argv) {
    try {
        require(argc == 2 || argc == 3, "usage: verify4x4 CERTIFICATE [OTHER_CERTIFICATE]");
        Board board;
        std::array<std::string, 2> bounds;
        for (int i = 1; i < argc; ++i) {
            Graph graph(argv[i]);
            require(bounds[graph.owner].empty(), "duplicate certificate owner");
            BestResponder response(graph, board);
            Mass wins = response.solve();
            bounds[graph.owner] = fraction(graph.owner == Black ? graph.total - wins : wins,
                                          graph.total);
            std::cout << (graph.owner == Black ? "lower_bound " : "upper_bound ")
                      << bounds[graph.owner] << '\n';
        }
        if (!bounds[0].empty() && bounds[0] == bounds[1]) {
            std::cout << "exact_value " << bounds[0] << '\n';
        }
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
