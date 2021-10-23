import sched
from typing import Any
from typing import Callable
from typing import Dict
from typing import Iterator
from typing import Iterable
from typing import Generator
from typing import List
from typing import Optional
from typing import Set
from typing import Tuple
from typing import Union
from typing import overload
from datetime import datetime
from typing_extensions import Literal
from plugins.scheduler import ScheduledEvent
from plugins.applog import SearchResult
from plugins.foodlog import SearchResult as FoodLogSearchResult
from sqlite3 import Row
from pathlib import Path


def block() -> None: ...


def log(
        message: str,
        level: Optional[int] = 20,
        traceback: Optional[bool] = False,
) -> None: ...


def subscribe(channel: str, callback: Callable) -> List[int]: ...


def start() -> None: ...


def exit() -> None: ...


@overload
def publish(
        channel: Literal["memorize:get"],
        key: str,
        default: Optional[str] = "",
) -> List[Tuple[bool, str]]: ...


@overload
def publish(
        channel: Literal["memorize:set"],
        key: str,
        value: Any,
) -> List[None]: ...


@overload
def publish(
        channel: Literal["memorize:clear"],
        key: str = ""
) -> List[bool]: ...


@overload
def publish(
        channel: Literal["url:current"],
) -> List[str]: ...


@overload
def publish(
        channel: Literal["url:internal"],
        path: str = "",
        query: Optional[Dict[str, Any]] = None,
) -> List[str]: ...


@overload
def publish(
        channel: Literal["clock:duration:words"],
        **kwargs: Union[str, int, float],
) -> List[str]: ...


@overload
def publish(
        channel: Literal["clock:month:start"],
        dt: datetime,
        fmt: Optional[str] = "",
) -> List[datetime]: ...


@overload
def publish(
        channel: Literal["clock:month:end"],
        dt: datetime,
        fmt: Optional[str] = "",
) -> List[datetime]: ...


@overload
def publish(
        channel: Literal["clock:month:next"],
        dt: datetime,
) -> List[datetime]: ...


@overload
def publish(
        channel: Literal["clock:month:previous"],
        dt: datetime,
) -> List[datetime]: ...


@overload
def publish(
        channel: Literal["clock:shift"],
        dt: datetime,
        **kwargs: Union[float, str]
) -> List[datetime]: ...


@overload
def publish(
        channel: Literal["clock:local"],
        dt: datetime,
) -> List[datetime]: ...


@overload
def publish(
        channel: Literal["clock:day:remaining"],
        dt: Optional[datetime] = None,
) -> List[int]: ...


@overload
def publish(
        channel: Literal["clock:utc"],
        dt: datetime,
) -> List[datetime]: ...


@overload
def publish(
        channel: Literal["clock:format"],
        dt: datetime,
        fmt: str,
) -> List[str]: ...


@overload
def publish(
        channel: Literal["clock:ago"],
        value: datetime,
) -> List[str]: ...


@overload
def publish(
        channel: Literal["clock:from_timestamp"],
        timestamp: Union[int, float],
        local: Optional[bool] = False
) -> List[datetime]: ...


@overload
def publish(
        channel: Literal["clock:same_day"],
        dt1: datetime,
        dt2: datetime,
) -> List[bool]: ...


@overload
def publish(
        channel: Literal["clock:now"],
        local: Optional[bool] = False,
) -> List[datetime]: ...


@overload
def publish(
        channel: Literal["clock:now_unix"],
) -> List[float]: ...


@overload
def publish(
        channel: Literal["clock:from_format"],
        value: str,
        fmt: str,
        local: Optional[bool] = False
) -> List[datetime]: ...


@overload
def publish(
        channel: Literal["url:readable"],
        path: str = ""
) -> List[str]: ...


@overload
def publish(
        channel: Literal["url:domain"],
        url: Optional[str],
) -> List[str]: ...


@overload
def publish(
        channel: Literal["url:alt"],
        path: str = ""
) -> List[str]: ...


@overload
def publish(
        channel: Literal["registry:add"],
        key: str,
        value: Any
) -> List[bool]: ...


@overload
def publish(
        channel: Literal["registry:added"],
        key: str,
) -> List[None]: ...


@overload
def publish(
        channel: Literal["registry:find"],
        value: Any,
        key_prefix: Optional[str] = ""
) -> List[Optional[Row]]: ...


@overload
def publish(
        channel: Literal["registry:keys"],
        depth: Optional[int] = 1
) -> List[Generator[Any, None, None]]: ...


@overload
def publish(
        channel: Literal["registry:remove:id"],
        rowid: int
) -> List[int]: ...


@overload
def publish(
        channel: Literal["registry:remove:key"],
        key: str
) -> List[int]: ...


@overload
def publish(
        channel: Literal["registry:search:multidict"],
        *args: Any,
        **kwargs: Any,
) -> List[Dict[str, Any]]: ...


@overload
def publish(
        channel: Literal["registry:search:valuelist"],
        *args: Any,
        **kwargs: Any,
) -> List[List[str]]: ...


@overload
def publish(
        channel: Literal["registry:update"],
        rowid: int,
        key: str,
        value: Any,
) -> List[bool]: ...


@overload
def publish(
        channel: Literal["registry:updated"],
        key: str,
) -> List[None]: ...


@overload
def publish(
        channel: Literal["registry:first:value"],
        key: str,
        memorize: Optional[bool] = False,
        as_path: Optional[bool] = False,
        default: Optional[Any] = None
) -> List[Any]: ...


@overload
def publish(
        channel: Literal["registry:first:key"],
        value: Any,
        key_prefix: str = ""
) -> List[str]: ...


@overload
def publish(
        channel: Literal["registry:replace"],
        key: str,
        value: Any
) -> List[None]: ...


@overload
def publish(
        channel: Literal["registry:search"],
        key: str,
        **kwargs: Any
) -> List[Tuple[int, Iterator[Row]]]: ...


@overload
def publish(
        channel: Literal["registry:search:dict"],
        *args: Any,
        **kwargs: Any,
) -> List[Dict[str, Any]]: ...


@overload
def publish(
        channel: Literal["jinja:render"],
        template: str,
        **kwargs: Any
) -> List[bytes]: ...


@overload
def publish(
        channel: Literal["scheduler:add"],
        delay_seconds: int,
        scheduled_channel: Literal["memorize:clear"],
        key: str,
) -> List[ScheduledEvent]: ...


@overload
def publish(
        channel: Literal["scheduler:add"],
        delay_seconds: int,
        scheduled_channel: str,
        *args: Optional[Any],
        **kwargs: Optional[Any],
) -> List[ScheduledEvent]: ...


@overload
def publish(
        channel: Literal["scheduler:persist"],
        delay_seconds: int,
        *args: Any,
        **kwargs: Any,
) -> List[ScheduledEvent]: ...


@overload
def publish(
        channel: Literal["scheduler:remove"],
        event: Union[str, sched.Event]
) -> List[bool]: ...


@overload
def publish(
        channel: Literal["scheduler:upcoming"],
        event_filter: str = ""
) -> List[List[sched.Event]]: ...


@overload
def publish(
        channel: Literal["cache:prune"],
) -> List[None]: ...


@overload
def publish(
        channel: Literal["cache:set"],
        key: str,
        value: Any,
        lifespan_seconds: float = 604800
) -> List[bool]: ...


@overload
def publish(
        channel: Literal["cache:clear"],
        key: str,
) -> List[Literal[True]]: ...


@overload
def publish(
        channel: Literal["cache:match"],
        prefix: str,
) -> List[Iterator[Any]]: ...


@overload
def publish(
        channel: Literal["applog:add"],
        source: str,
        message: Any
) -> List[None]: ...


@overload
def publish(
        channel: Literal["applog:pull"]
) -> List[None]: ...


@overload
def publish(
        channel: Literal["applog:newest"],
        source: str
) -> List[Optional[str]]: ...


@overload
def publish(
        channel: Literal["applog:prune"],
        cutoff_months: int = 3
) -> List[None]: ...


@overload
def publish(
        channel: Literal["applog:search"],
        **kwargs: Any
) -> List[SearchResult]: ...


@overload
def publish(
        channel: Literal["applog:sources"],
) -> List[Iterator[Row]]: ...


@overload
def publish(
        channel: Literal["applog:view"],
        **kwargs: Any
) -> List[SearchResult]: ...


@overload
def publish(
        channel: Literal["assets:hash"],
        target: Path,
) -> List[str]: ...


@overload
def publish(
        channel: Literal["assets:get"],
        target: Path,
) -> List[Tuple[bytes, str]]: ...


@overload
def publish(
        channel: Literal["assets:publish"],
        reset: Optional[bool] = False,
) -> List[None]: ...


@overload
def publish(
        channel: Literal["cache:get"],
        key: str
) -> List[Any]: ...


@overload
def publish(
        channel: Literal["notifier:build"],
        **kwargs: Any
) -> List[Dict[str, Any]]: ...


@overload
def publish(
        channel: Literal["notifier:clear"],
        local_id: Optional[str] = ""
) -> List[bool]: ...


@overload
def publish(
        channel: Literal["notifier:send"],
        notification: Dict[str, str]
) -> List[bool]: ...


@overload
def publish(
        channel: Literal["bookmarks:tags:all"],
        for_precache: bool = False
) -> List[Union[None, List[str]]]: ...


@overload
def publish(
        channel: Literal["bookmarks:remove"],
        uid: int,
) -> List[int]: ...


@overload
def publish(
        channel: Literal["bookmarks:search"],
        query: str,
        **kwargs: Any,
) -> List[Tuple[Iterator[Row], int, List[str]]]: ...


@overload
def publish(
        channel: Literal["bookmarks:recent"],
        limit: int = 20,
        offset: int = 0,
        max_days: int = 180
) -> List[Tuple[Iterator[Row], int, List[str]]]: ...


@overload
def publish(
        channel: Literal["bookmarks:domaincount"],
        domain: str,
        path: str = "",
) -> List[int]: ...


@overload
def publish(
        channel: Literal["bookmarks:find"],
        uid: str = "",
        url: str = "",
) -> List[Optional[Row]]: ...


@overload
def publish(
        channel: Literal["bookmarks:add"],
        url: str,
        title: str = "",
        comments: str = "",
        tags: str = "",
        added: str = ""
) -> List[bool]: ...


@overload
def publish(
        channel: Literal["bookmarks:add:fulltext"]
) -> List[None]: ...


@overload
def publish(
        channel: Literal["bookmarks:prune"],
) -> List[None]: ...


@overload
def publish(
        channel: Literal["bookmarks:repair"],
) -> List[None]: ...


@overload
def publish(
        channel: Literal["registry:removed"],
        key: str,
) -> List[None]: ...


@overload
def publish(
        channel: Literal["formatting:dbpedia_abstract"],
        text: str,
) -> List[str]: ...


@overload
def publish(
        channel: Literal["formatting:string_sanitize"],
        value: str,
        also_allowed: str = ''
) -> List[str]: ...


@overload
def publish(
        channel: Literal["formatting:phone_sanitize"],
        number: str,
) -> List[str]: ...


@overload
def publish(
        channel: Literal["cdr:timeline"],
        src_exclude: List[str] = [],
        dst_exclude: List[str] = [],
        offset: int = 0,
        limit: int = 50
) -> List[Tuple[List[Row], int]]: ...


@overload
def publish(
        channel: Literal["cdr:history"],
        number: str,
        limit: int = 50
) -> List[Tuple[List[Row], int]]: ...


@overload
def publish(
        channel: Literal["capture:add"],
        request: Any,
        response: Any
) -> List[bool]: ...


@overload
def publish(
        channel: Literal["capture:search"],
        path: Optional[str] = None,
        offset: int = 0,
        limit: int = 10
) -> List[Tuple[int, List[Row]]]: ...


@overload
def publish(
        channel: Literal["capture:get"],
        rowid: int
) -> List[Optional[Row]]: ...


@overload
def publish(
        channel: Literal["capture:prune"],
        cutoff_months: int = 3
) -> List[None]: ...


@overload
def publish(
        channel: Literal["foodlog:find"],
        entry_id: int
) -> List[Optional[Row]]: ...


@overload
def publish(
        channel: Literal["foodlog:remove"],
        entry_id: int
) -> List[bool]: ...


@overload
def publish(
        channel: Literal["foodlog:search:date"],
        **kwargs: Any,
) -> List[FoodLogSearchResult]: ...


@overload
def publish(
        channel: Literal["foodlog:search:keyword"],
        **kwargs: Any
) -> List[FoodLogSearchResult]: ...


@overload
def publish(
        channel: Literal["foodlog:upsert"],
        recipe_id: int,
        **kwargs: Any
) -> List[bool]: ...


@overload
def publish(
        channel: Literal["ip:db:modified"],
) -> List[float]: ...


@overload
def publish(
        channel: Literal["ip:facts"],
        ip_address: str,
) -> List[Dict[str, str]]: ...


@overload
def publish(
        channel: Literal["ip:reverse"],
        ip_address: str,
) -> List[Dict[str, Any]]: ...


@overload
def publish(
        channel: Literal["urlfetch:get"],
        url: str,
) -> List[Any]: ...


@overload
def publish(
        channel: Literal["urlfetch:get:json"],
        url: str,
        *,
        auth: Iterable[str] = (),
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, Any]] = None,
        cache_lifespan: int = 0
) -> List[Any]: ...


@overload
def publish(
        channel: Literal["urlfetch:get"],
        url: str,
        as_object: Literal[True],
        **kwargs: Any,
) -> List[Any]: ...


@overload
def publish(
        channel: Literal["urlfetch:delete"],
        url: str,
        **kwargs: Any
) -> List[bool]: ...


@overload
def publish(
        channel: Literal["urlfetch:get:file"],
        url: str,
        destination: Path,
        as_json: Optional[bool] = False,
        **kwargs: Any
) -> List[None]: ...


@overload
def publish(
        channel: Literal["urlfetch:post"],
        url: str,
        data: Optional[Any],
        **kwargs: Any
) -> List[Any]: ...


@overload
def publish(
        channel: Literal["urlfetch:post"],
        url: str,
        data: Any,
        as_object: bool,
        **kwargs: Any
) -> List[Any]: ...


@overload
def publish(
        channel: Literal["urlfetch:post"],
        url: str,
        data: Any,
        as_json: bool,
        **kwargs: Any
) -> List[Any]: ...


@overload
def publish(
        channel: Literal["urlfetch:post"],
        url: str,
        data: Any,
        as_bytes: bool,
        **kwargs: Any
) -> List[Any]: ...


@overload
def publish(
        channel: Literal["markup:reduce:title"],
        title: str,
) -> List[str]: ...


@overload
def publish(
        channel: Literal["markup:plaintext"],
        html: str = "",
        url: str = "",
) -> List[str]: ...


@overload
def publish(
        channel: Literal["metrics:pull"]
) -> List[None]: ...


@overload
def publish(
        channel: Literal["metrics:add"],
        key: str,
        value: float,
        unit: str,
) -> List[None]: ...


@overload
def publish(
        channel: Literal["metrics:inventory"],
) -> List[Iterator[Row]]: ...


@overload
def publish(
        channel: Literal["metrics:prune"],
        cutoff_months: int = 6
) -> List[None]: ...


@overload
def publish(
        channel: Literal["metrics:dataset"],
        key: str
) -> List[Iterator[Row]]: ...


@overload
def publish(
        channel: Literal["hasher:value"],
        value: Union[str, bytes],
        algorithm: str = "sha256",
) -> List[str]: ...


@overload
def publish(
        channel: Literal["hasher:file"],
        path: str,
        algorithm: str = "sha256",
        memorize: bool = True
) -> List[str]: ...


@overload
def publish(
        channel: Literal["logindex:parse"],
        batch_size: Optional[int] = 100,
) -> List[None]: ...


@overload
def publish(
        channel: Literal["logindex:reversal"],
        batch_size: Optional[int] = 100,
) -> List[None]: ...


@overload
def publish(
        channel: Literal["logindex:alert"],
        earliest_id: int,
        count: int,
) -> List[None]: ...


@overload
def publish(
        channel: Literal["logindex:enqueue"],
        start_date: datetime,
        end_date: datetime,
) -> List[None]: ...


@overload
def publish(
        channel: Literal["logindex:insert_line"],
        records: Iterable[Any],
) -> List[None]: ...


@overload
def publish(
        channel: Literal["logindex:append_line"],
        records: List[Tuple[str, str]],
) -> List[None]: ...


@overload
def publish(
        channel: Literal["logindex:count_lines"],
        source: Path,
) -> List[int]: ...


@overload
def publish(
        channel: Literal["logindex:process_queue"],
) -> List[None]: ...


@overload
def publish(
        channel: Literal["logindex:query"],
        query: str,
) -> List[Tuple[List[Row], List[str]]]: ...


@overload
def publish(
        channel: Literal["logindex:query:reverse_ip"],
        ips: Set[str] = set(),
) -> List[Dict[str, str]]: ...


@overload
def publish(
        channel: Literal["logindex:count_visit_days"],
        ip_address: str,
) -> List[Dict[str, Union[int, str]]]: ...


@overload
def publish(
        channel: Literal["logindex:repair"],
) -> List[None]: ...


@overload
def publish(
        channel: Literal["geography:unabbreviate_state"],
        abbreviation: str,
) -> List[Tuple[str, Optional[str]]]: ...


@overload
def publish(
        channel: Literal["geography:state_by_area_code"],
        area_code: str
) -> List[Tuple[str, Optional[str], Optional[str]]]: ...


@overload
def publish(
        channel: Literal["geography:country_by_abbreviation"],
        abbreviations: Iterable[str] = ()
) -> List[Dict[str, str]]: ...


@overload
def publish(
        channel: Literal["recipes:attachment:list"],
        recipe_id: int,
) -> List[List[Row]]: ...


@overload
def publish(
        channel: Literal["recipes:attachment:view"],
        recipe_id: int,
        filename: str,
) -> List[Row]: ...


@overload
def publish(
        channel: Literal["recipes:attachment:remove"],
        recipe_id: int,
        attachment_id: int,
) -> List[bool]: ...


@overload
def publish(
        channel: Literal["recipes:tags:all"],
) -> List[Iterator[Row]]: ...


@overload
def publish(
        channel: Literal["recipes:find"],
        recipe_id: int,
) -> List[Optional[Row]]: ...


@overload
def publish(
        channel: Literal["recipes:find:tag"],
        tag: str,
) -> List[Iterator[Row]]: ...


@overload
def publish(
        channel: Literal["recipes:find:recent"],
        limit: Optional[int] = 12,
) -> List[Iterator[Row]]: ...


@overload
def publish(
        channel: Literal["recipes:find:starred"],
        limit: Optional[int] = 20,
) -> List[Iterator[Row]]: ...


@overload
def publish(
        channel: Literal["recipes:prune"],
) -> List[None]: ...


@overload
def publish(
        channel: Literal["recipes:remove"],
        recipe_id: int,
) -> List[bool]: ...


@overload
def publish(
        channel: Literal["recipes:search:date"],
        field: str,
        query_date: datetime,
) -> List[Iterator[Row]]: ...


@overload
def publish(
        channel: Literal["recipes:search:keyword"],
        query: str,
) -> List[Iterator[Row]]: ...


@overload
def publish(
        channel: Literal["recipes:toggle:star"],
        recipe_id: int,
) -> List[None]: ...


@overload
def publish(
        channel: Literal["recipes:upsert"],
        recipe_id: int,
        **kwargs: Any,
) -> List[Union[bool, int]]: ...


@overload
def publish(
        channel: Literal["speak:muted"],
) -> List[bool]: ...


@overload
def publish(
        channel: Literal["speak:muted:scheduled"],
) -> List[bool]: ...


@overload
def publish(
        channel: Literal["speak:muted:temporarily"],
) -> List[bool]: ...


@overload
def publish(
        channel: Literal["speak:mute"],
) -> List[None]: ...


@overload
def publish(
        channel: Literal["speak:unmute"],
) -> List[None]: ...


@overload
def publish(
        channel: Literal["speak:voices"],
) -> List[Dict[str, str]]: ...


@overload
def publish(
        channel: Literal["speak"],
        statement: str,
        locale: Optional[str] = "en-GB",
        gender: Optional[str] = "Male",
        name: Optional[str] = "en-GB-RyanNeural",
) -> List[bool]: ...


@overload
def publish(
        channel: Literal["weather:forecast"],
        config: Dict[str, Any],
) -> List[Dict[str, Any]]: ...


@overload
def publish(
        channel: Literal["weather:prefetch"],
) -> List[None]: ...


@overload
def publish(
        channel: Literal["weather:config"],
        latitude: str,
        longitude: str,
) -> List[Dict[str, Any]]: ...


@overload
def publish(
        channel: Literal["audio:play_bytes"],
        audio_bytes: bytes
) -> List[None]: ...


@overload
def publish(
        channel: Literal["audio:play:asset"],
        name: str,
) -> List[None]: ...


@overload
def publish(
        channel: Literal["gcp:appengine:ingest_file"],
        storage_path: Path,
        batch_size: Optional[int] = 100,
) -> List[None]: ...


@overload
def publish(
        channel: Literal["filesystem:read"],
        target: Path,
) -> List[bytes]: ...


@overload
def publish(
        channel: Literal["filesystem:walk"],
        extensions: Tuple[str, ...],
) -> List[Iterator[Path]]: ...


@overload
def publish(
        channel: Literal["server:ready"],
) -> List[None]: ...


@overload
def publish(
        channel: Literal["cache:ready"],
) -> List[None]: ...
